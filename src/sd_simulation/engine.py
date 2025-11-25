from typing import Dict, List, Tuple, Optional, Callable, Any
import numpy as np
from enum import Enum
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pyvis.network import Network
# import networkx as nx

class VariableType(Enum):
    STOCK = "stock"
    FLOW = "flow"
    AUXILIARY = "auxiliary"
    CONSTANT = "constant"

class SimVariable:
    """
    Representa uma variável em um modelo de dinâmica de sistemas.
    Seu comportamento (taxa de mudança para STOCKs, valor para AUXILIARYs)
    é definido por uma função de equação.
    """
    
    def __init__(self, name: str, initial_value: float = 0.0, 
                 var_type: VariableType = VariableType.STOCK,
                 accept_negative: bool = True, min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 equation_func: Optional[Callable[['SimVariable', Any], float]] = None):
        self.name = name
        self.initial_value = initial_value
        self.value = initial_value
        self.var_type = var_type
        self.history: List[float] = [initial_value]
        self.accept_negative = accept_negative
        self.min_value = min_value
        self.max_value = max_value
        self._equation_func = equation_func
        
        if not accept_negative and min_value is None:
            self.min_value = 0.0

    @property
    def v(self) -> float:
        """Retorna o valor atual da variável para acesso conciso."""
        return self.value

    def set_equation(self, func: Callable[['SimVariable', Dict[str, 'SimVariable']], float]) -> None:
        """Define a função de cálculo para esta variável."""
        self._equation_func = func

    def calculate_delta(self, model_object: Any) -> float:
        """
        Calcula a taxa de mudança (delta) para este passo de tempo.
        Aplicável principalmente a STOCKs.
        """
        if self.var_type == VariableType.CONSTANT:
            return 0.0
        
        if self.var_type == VariableType.STOCK and self._equation_func:
            return self._equation_func(self, model_object)
            
        return 0.0 # Auxiliares e FLOWs não calculam delta aqui, seu valor é definido em update
    
    def update(self, dt: float, model_object: Any, delta_value: Optional[float] = None) -> None:
        """
        Atualiza o valor da variável para o próximo passo de tempo.
        Para AUXILIARYs, calcula o valor diretamente.
        Para STOCKs, usa o delta_value fornecido.
        """
        if self.var_type == VariableType.CONSTANT:
            new_value = self.value

        new_value = self.value
        if self.var_type == VariableType.AUXILIARY and self._equation_func:
            new_value = self._equation_func(self, model_object)
        elif self.var_type == VariableType.STOCK and delta_value is not None:
            new_value = self.value + delta_value * dt
        
        if self.min_value is not None:
            new_value = max(self.min_value, new_value)
        if self.max_value is not None:
            new_value = min(self.max_value, new_value)
                
        self.value = new_value
            
        self.history.append(self.value)
    
    def reset(self) -> None:
        """Reinicia a variável para o estado inicial."""
        self.value = self.initial_value
        self.history = [self.initial_value]

class Simulation:
    """
    Motor de simulação de dinâmica de sistemas.
    Gerencia a execução do modelo, a integração no tempo e a detecção de equilíbrio.
    """
    
    def __init__(self, model_object: object, 
                 time_steps: int = 50, dt: float = 1.0):
        self._model_object = model_object
        self._variables: Dict[str, SimVariable] = {}
        # Debugging: Check what attributes are being found
        self._variables: Dict[str, SimVariable] = {}
        for attr_name in dir(model_object):
            attr_value = getattr(model_object, attr_name)
            if isinstance(attr_value, SimVariable):
                self._variables[attr_name] = attr_value
        
        if not self._variables:
            raise ValueError("No SimVariable instances found in the provided model object.")

        self.time_steps = time_steps
        self.dt = dt
        self.current_step = 0
        
        self.equilibrium_detection = True
        self.equilibrium_threshold = 1e-6
        self.equilibrium_window = 10
        
    def step(self) -> None:
        """Executa um passo da simulação."""
        if self.current_step >= self.time_steps - 1:
            return
        
        self._euler_step()
            
        self.current_step += 1
    
    def _euler_step(self) -> None:
        """
        Passo de integração Euler com funções de equação.
        Garante a ordem correta de cálculo: STOCKs (deltas), STOCKs (atualização), AUXILIARYs.
        """
        # 1. Calcular todos os deltas (taxas de mudança) para os STOCKs
        stock_deltas = {}
        for name, var in self._variables.items():
            if var.var_type == VariableType.STOCK:
                stock_deltas[name] = var.calculate_delta(self._model_object)

        # 2. Atualizar os valores dos STOCKs usando os deltas calculados
        for name, var in self._variables.items():
            if var.var_type == VariableType.STOCK:
                var.update(self.dt, self._model_object, delta_value=stock_deltas.get(name, 0.0))

        # 3. Atualizar os valores das AUXILIARYs
        #    A ordem de cálculo das AUXILIARYs é crucial se houver dependências entre elas.
        #    Para um sistema robusto, seria necessária uma ordenação topológica das dependências.
        #    Por simplicidade, vamos iterar e atualizar.
        for name, var in self._variables.items():
            if var.var_type == VariableType.AUXILIARY:
                var.update(self.dt, self._model_object)
        
        for name, var in self._variables.items():
            if var.var_type == VariableType.CONSTANT:
                var.update(self.dt, self._model_object)
    
    def run(self) -> None:
        """Executa a simulação completa."""
        self.reset()
        for step_num in range(self.time_steps - 1):
            self.step()
            
            if self.equilibrium_detection and self._check_equilibrium():
                print(f"Equilíbrio alcançado no passo {step_num + 1}")
                break
    
    def _check_equilibrium(self) -> bool:
        """Verifica se o sistema atingiu o equilíbrio."""
        if self.current_step < self.equilibrium_window:
            return False
        
        for var in self._variables.values():
            if var.var_type == VariableType.CONSTANT:
                continue
            
            recent_values = var.history[-self.equilibrium_window:]
            if len(recent_values) < self.equilibrium_window:
                return False
            
            max_change = max(abs(recent_values[i] - recent_values[i-1]) 
                           for i in range(1, len(recent_values)))
            if max_change > self.equilibrium_threshold:
                return False
        
        return True
    
    def reset(self) -> None:
        """Reinicia a simulação para o estado inicial."""
        self.current_step = 0
        for var in self._variables.values():
            var.reset()
    
    def get_results(self) -> Dict[str, List[float]]:
        """Obtém os resultados da simulação como um dicionário de históricos."""
        return {name: var.history.copy() for name, var in self._variables.items()}
    
    def get_time_series(self) -> List[float]:
        """Obtém a série temporal para plotagem."""
        return [i * self.dt for i in range(len(next(iter(self._variables.values())).history))]
    
    def get_phase_space(self, var1_name: str, var2_name: str) -> Tuple[List[float], List[float]]:
        """Obtém a trajetória do espaço de fase para duas variáveis."""
        var1_history = self._variables[var1_name].history
        var2_history = self._variables[var2_name].history
        return var1_history, var2_history

    def plot_dependencies_graph(self, 
                                dependencies_graph: Dict[str, List[str]],
                                graph_name: str = "dependency",
                                save_path: str = "notebooks/dependency.html") -> None:
        """
        Plota o grafo de dependências usando PyVis.

        Args:
            dependencies_graph (Dict[str, List[str]]): O grafo de dependências gerado por get_dependencies_graph.
            graph_name (str): Nome do grafo para o título.
            save_path (str): Caminho para salvar o gráfico como um arquivo HTML.
        """
        net = Network(notebook=True, height="1024px", width="100%", 
                      cdn_resources='remote', directed=True)
        net.toggle_physics(True) # Habilita física para melhor layout inicial
        
        # Adicionar nós
        all_nodes = set()
        for node, deps in dependencies_graph.items():
            all_nodes.add(node)
            for dep in deps:
                all_nodes.add(dep)

        for node in all_nodes:
            net.add_node(node, label=node), #title=node, 
                         #color="#009688", size=45) # Further increased node size

        # Adicionar arestas
        for node, deps in dependencies_graph.items():
            for dep in deps:
                net.add_edge(dep, node)#, arrows="to", color="#9E9E9E") # Cor cinza para arestas
        
        net.set_options(
            """
            const options = {
                "physics": {
                    "barnesHut": {
                    "gravitationalConstant": -6800
                    },
                    "minVelocity": 0.75
                }
            }            
        """
        )
        # net.show_buttons(filter_=['physics'])
        net.write_html(save_path)
        print(f"Grafo de dependências '{graph_name}' salvo em: {save_path}")

    def plot_simulation_results(self,
                                variables_to_plot: Optional[List[str]] = None,
                                secondary_y_variables: Optional[List[str]] = None,
                                save_path: Optional[str] = None) -> None:
        """
        Plota o histórico das variáveis da simulação usando Plotly.

        Args:
            variables_to_plot (Optional[List[str]]): Lista de nomes das variáveis a serem plotadas.
                                                      Se None ou vazia, todas as variáveis serão plotadas.
            secondary_y_variables (Optional[List[str]]): Lista de nomes das variáveis a serem plotadas
                                                         no eixo Y secundário.
            save_path (Optional[str]): Caminho para salvar o gráfico como um arquivo HTML.
                                       Se None, o gráfico será exibido interativamente.
        """
        results = self.get_results()
        time_series = self.get_time_series()
        
        if not results:
            print("Nenhum resultado de simulação para plotar.")
            return

        if variables_to_plot is None or not variables_to_plot:
            variables_to_plot = list(results.keys())
        
        if secondary_y_variables is None:
            secondary_y_variables = []

        # Determine if a secondary y-axis is needed
        specs = [[{"secondary_y": True}]] if any(v in secondary_y_variables for v in variables_to_plot) else [[{}]]
        fig = make_subplots(rows=1, cols=1, specs=specs)

        for var_name in variables_to_plot:
            if var_name in results:
                is_secondary = var_name in secondary_y_variables
                fig.add_trace(
                    go.Scatter(x=time_series, y=results[var_name], mode='lines', name=var_name),
                    secondary_y=is_secondary,
                )
            else:
                print(f"Aviso: Variável '{var_name}' não encontrada nos resultados da simulação.")

        fig.update_layout(
            title_text="Histórico da Simulação",
            xaxis_title="Tempo",
            hovermode="x unified"
        )
        fig.update_yaxes(title_text="Valor (Eixo Principal)", secondary_y=False)
        if any(v in secondary_y_variables for v in variables_to_plot):
            fig.update_yaxes(title_text="Valor (Eixo Secundário)", secondary_y=True)

        if save_path:
            fig.write_html(save_path)
            print(f"Gráfico salvo em: {save_path}")
        else:
            fig.show()


    def get_dependencies_graph(self) -> Dict[str, List[str]]:
        """
        Gera um grafo de dependências das variáveis, mostrando quais variáveis
        são acessadas pelas funções de equação de outras variáveis.
        """
        dependencies_graph: Dict[str, List[str]] = {}

        for target_var_name, target_var_obj in self._variables.items():
            if target_var_obj.var_type == VariableType.CONSTANT or target_var_obj._equation_func is None:
                continue # Constantes não têm dependências calculadas por função

            # Criar um mock do objeto do modelo para detectar acessos
            mock_model_object = type(self._model_object)() # Create an empty instance of the model class
            mock_variables_map: Dict[str, MockSimVariable] = {}

            for attr_name in dir(self._model_object):
                attr_value = getattr(self._model_object, attr_name)
                if isinstance(attr_value, SimVariable):
                    mock_sim_var = MockSimVariable(attr_name, initial_value=attr_value.initial_value)
                    setattr(mock_model_object, attr_name, mock_sim_var)
                    mock_variables_map[attr_name] = mock_sim_var

            # Executar a função de equação com o mock do modelo
            try:
                target_var_obj._equation_func(target_var_obj, mock_model_object)
            except Exception as e:
                print(f"Aviso: Erro ao analisar dependências para {target_var_name}: {e}")
                continue

            # Coletar as variáveis que foram acessadas
            current_deps = [
                mock.name for mock in mock_variables_map.values()
                if mock._accessed_by_equation
            ]
            dependencies_graph[target_var_name] = sorted(list(set(current_deps)))

        return dependencies_graph

class MockSimVariable:
    """
    Um mock de SimVariable usado para detectar dependências de variáveis
    ao executar funções de equação.
    """
    def __init__(self, name: str, initial_value: float = 0.0, var_type: VariableType = VariableType.STOCK):
        self.name = name
        self._accessed_by_equation: bool = False
        self.value = initial_value # Valor dummy
        self.var_type = var_type # Needed for dependency graph to correctly identify constants

    @property
    def v(self) -> float:
        """Registra o acesso e retorna um valor dummy."""
        self._accessed_by_equation = True
        return self.value

    def reset_access_flag(self) -> None:
        """Reseta a flag de acesso."""
        self._accessed_by_equation = False
