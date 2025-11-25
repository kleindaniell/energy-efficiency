from sd_simulation.engine import SimVariable, VariableType
from typing import Any


class FapergsRGEBaseModel:
    def __init__(self, consumo_medio_inicial=113, producao_inicial=450_000_000):
        
        THETA_CALIBRADO = consumo_medio_inicial / producao_inicial
        
        # --- PARÂMETROS GERAIS ---
        self.TARIFA_R_MWh = SimVariable("Tarifa_Energia", 650.0, VariableType.CONSTANT)
        self.ICMS_ALIQUOTA = SimVariable("Aliquota_ICMS", 0.17, VariableType.CONSTANT)
        self.FORCA_POLITICA = SimVariable("Forca_Politica_Publica", 0, VariableType.CONSTANT)
        self.CAPACIDADE_MAXIMA = SimVariable("Capacidade_Maxima_Mercado", 500_000_000.0, VariableType.CONSTANT)
        
        # --- PARÂMETROS DE TEMPO (DELAYS) ---
        self.TEMPO_RESPOSTA_MERCADO = SimVariable("Tempo_Resposta_Mercado", 12.0, VariableType.CONSTANT)
        # MELHORIA 3: Tempo para gastar o capital (executar obras de EE)
        self.TEMPO_IMPLEMENTACAO = SimVariable("Tempo_Implementacao_Projetos", 6.0, VariableType.CONSTANT)

        # --- PARÂMETROS TÉCNICOS E DE CALIBRAÇÃO ---
        self.theta_intensidade = SimVariable("Intensidade_Energetica_Inicial", THETA_CALIBRADO, VariableType.CONSTANT)
        self.limite_eficiencia = SimVariable("Limite_Tecnico_Eficiencia", 0.60, VariableType.CONSTANT)
        
        # MELHORIA 1: Parametrização dos "Números Mágicos"
        self.TAXA_REINVESTIMENTO = SimVariable("Pct_Reinvestimento_Faturamento", 0.005, VariableType.CONSTANT)
        self.CAPITAL_SATURACAO = SimVariable("Capital_Saturacao_Marginal", 1_000_000.0, VariableType.CONSTANT)
        self.CUSTO_EFICIENCIA = SimVariable("Custo_Para_Ganho_Eficiencia", 100_000.0, VariableType.CONSTANT)

        # Sensibilidades
        self.sensib_invest_eff = SimVariable("Sensib_Invest_Eficiencia", 0.0005, VariableType.CONSTANT)
        self.sensib_comp_prod = SimVariable("Sensib_Competitividade_Producao", 0.02, VariableType.CONSTANT)
        self.fator_rebote = SimVariable("Fator_Rebote", 0.15, VariableType.CONSTANT)

        # --- ESTOQUES ---
        self.eficiencia = SimVariable("Estoque_Eficiencia", 0.10, VariableType.STOCK,
                                      min_value=0.0, max_value=0.60,
                                      equation_func=self._eq_estoque_eficiencia)

        self.capital_investimento = SimVariable("Capital_Investimento_EE", 0.0, VariableType.STOCK,
                                                equation_func=self._eq_capital_investimento)

        self.producao = SimVariable("Producao_Industrial", producao_inicial, VariableType.STOCK,
                                    equation_func=self._eq_producao)

        self.competitividade = SimVariable("Indice_Competitividade", 1.0, VariableType.STOCK,
                                           equation_func=self._eq_competitividade_stock_flow)

        # --- VARIÁVEIS AUXILIARES ---
        # MELHORIA 2: Expondo o alvo para monitoramento
        self.competitividade_alvo = SimVariable("Competitividade_Potencial_Alvo", 1.0, VariableType.AUXILIARY,
                                                equation_func=self._eq_competitividade_alvo)

        self.consumo_energia = SimVariable("Consumo_Energia", 0.0, VariableType.AUXILIARY,
                                           equation_func=self._eq_consumo)

        self.gasto_implementacao = SimVariable("Fluxo_Gasto_Implementacao", 0.0, VariableType.AUXILIARY,
                                               equation_func=self._eq_gasto_implementacao)

        # --- ARRECADAÇÃO (Mantido igual) ---
        self.icms_energia = SimVariable("Arrecadacao_ICMS_Energia", 0.0, VariableType.AUXILIARY,
                                        equation_func=self._eq_icms_energia)
        self.icms_producao = SimVariable("Arrecadacao_ICMS_Producao", 0.0, VariableType.AUXILIARY,
                                         equation_func=self._eq_icms_producao)
        self.icms_total = SimVariable("Arrecadacao_Total", 0.0, VariableType.AUXILIARY,
                                      equation_func=self._eq_icms_total)

    # --- EQUAÇÕES ---

    @staticmethod
    def _eq_gasto_implementacao(self_var: SimVariable, vars: Any) -> float:
        # MELHORIA 3: Lógica baseada em tempo de atraso (Delay de 1ª ordem no fluxo)
        # A força política pode acelerar o tempo (reduzir o denominador)
        fator_aceleracao = 1.0 + (0.5 * vars.FORCA_POLITICA.v) # Política reduz o tempo
        tempo_real = vars.TEMPO_IMPLEMENTACAO.v / fator_aceleracao
        return vars.capital_investimento.v / tempo_real

    @staticmethod
    def _eq_capital_investimento(self_var: SimVariable, vars: Any) -> float:
        # MELHORIA 1: Uso de parâmetros explícitos
        reinvestimento_potencial = vars.producao.v * vars.TAXA_REINVESTIMENTO.v
        
        # Efeito de saturação (Balanceamento)
        fator_freio = 1 + (vars.capital_investimento.v / vars.CAPITAL_SATURACAO.v)
        reinvestimento_real = reinvestimento_potencial / fator_freio
        
        aporte_governo = 50_000 * vars.FORCA_POLITICA.v
        saida_gasto = vars.gasto_implementacao.v
        
        return (reinvestimento_real + aporte_governo) - saida_gasto

    @staticmethod
    def _eq_estoque_eficiencia(self_var: SimVariable, vars: Any) -> float:
        gap_tecnologico = vars.limite_eficiencia.v - vars.eficiencia.v
        
        # MELHORIA 1: Uso do parâmetro CUSTO_EFICIENCIA
        # A lógica física: Dinheiro investido / Custo unitário = Unidades de eficiência ganhas
        ganho = gap_tecnologico * vars.sensib_invest_eff.v * (vars.gasto_implementacao.v / vars.CUSTO_EFICIENCIA.v)
        
        depreciacao = vars.eficiencia.v * 0.01
        return ganho - depreciacao

    # MELHORIA 2: Função auxiliar pura para calcular o alvo
    @staticmethod
    def _eq_competitividade_alvo(self_var: SimVariable, vars: Any) -> float:
        return 1.0 + (vars.eficiencia.v * 0.1)

    @staticmethod
    def _eq_competitividade_stock_flow(self_var: SimVariable, vars: Any) -> float:
        # Usa a variável auxiliar criada acima
        alvo = vars.competitividade_alvo.v
        atual = vars.competitividade.v
        delay = vars.TEMPO_RESPOSTA_MERCADO.v
        return (alvo - atual) / delay

    @staticmethod
    def _eq_producao(self_var: SimVariable, vars: Any) -> float:
        taxa_crescimento_base = 0.001
        fator_competitividade = (vars.competitividade.v - 1.0) * vars.sensib_comp_prod.v
        r = taxa_crescimento_base + fator_competitividade
        
        P = vars.producao.v
        K = vars.CAPACIDADE_MAXIMA.v
        
        # Logistic Growth
        fluxo_producao = r * P * (1 - (P / K))
        return max(0, fluxo_producao)

    # --- Equações de Consumo e ICMS mantidas iguais ---
    @staticmethod
    def _eq_consumo(self_var: SimVariable, vars: Any) -> float:
        consumo_teorico = vars.theta_intensidade.v * vars.producao.v
        fator_eficiencia = (1 - vars.eficiencia.v)
        rebote = vars.fator_rebote.v * (consumo_teorico * vars.eficiencia.v)
        return (consumo_teorico * fator_eficiencia) + rebote

    @staticmethod
    def _eq_icms_energia(self_var: SimVariable, vars: Any) -> float:
        return vars.consumo_energia.v * vars.TARIFA_R_MWh.v * vars.ICMS_ALIQUOTA.v

    @staticmethod
    def _eq_icms_producao(self_var: SimVariable, vars: Any) -> float:
        return vars.producao.v * 0.12

    @staticmethod
    def _eq_icms_total(self_var: SimVariable, vars: Any) -> float:
        return vars.icms_energia.v + vars.icms_producao.v