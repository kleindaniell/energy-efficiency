from typing import Any
from sd_simulation.engine import SimVariable, VariableType, Simulation

# --- DADOS DE CALIBRAÇÃO ---
# Mantemos os mesmos valores calibrados anteriormente
CONSUMO_MEDIO_INICIAL_MWH = 3450.0
PRODUCAO_INICIAL_BRL = 450_000_000.0
THETA_CALIBRADO = CONSUMO_MEDIO_INICIAL_MWH / PRODUCAO_INICIAL_BRL

class FapergsRGEModelRefactored:
    """
    Modelo ajustado para consistência dimensional e limites físicos.
    CORREÇÃO: As equações agora referenciam os atributos Python corretos.
    """
    def __init__(self):
        # --- PARÂMETROS (CONSTANTES) ---
        # Nota: Os nomes dos atributos (self.NOME) são os que devem ser usados nas equações
        self.TARIFA_R_MWh = SimVariable("Tarifa_Energia", 650.0, VariableType.CONSTANT)
        self.ICMS_ALIQUOTA = SimVariable("Aliquota_ICMS", 0.17, VariableType.CONSTANT)
        self.FORCA_POLITICA = SimVariable("Forca_Politica_Publica", 0, VariableType.CONSTANT)
        
        # Parâmetros Técnicos
        self.theta_intensidade = SimVariable("Intensidade_Energetica_Inicial", THETA_CALIBRADO, VariableType.CONSTANT)
        self.limite_eficiencia = SimVariable("Limite_Tecnico_Eficiencia", 0.60, VariableType.CONSTANT)
        
        # Sensibilidades
        self.sensib_invest_eff = SimVariable("Sensib_Invest_Eficiencia", 0.0005, VariableType.CONSTANT)
        self.sensib_comp_prod = SimVariable("Sensib_Competitividade_Producao", 0.02, VariableType.CONSTANT)
        self.fator_rebote = SimVariable("Fator_Rebote", 0.15, VariableType.CONSTANT)

        # --- ESTOQUES ---
        self.eficiencia = SimVariable("Estoque_Eficiencia", 0.10, VariableType.STOCK, 
                                      min_value=0.0, max_value=0.60, 
                                      equation_func=self._eq_estoque_eficiencia)

        self.capital_investimento = SimVariable("Capital_Investimento_EE", 1_000_000.0, VariableType.STOCK,
                                                equation_func=self._eq_capital_investimento)

        self.producao = SimVariable("Producao_Industrial", PRODUCAO_INICIAL_BRL, VariableType.STOCK,
                                    equation_func=self._eq_producao)

        # --- VARIÁVEIS AUXILIARES ---
        self.consumo_energia = SimVariable("Consumo_Energia", 0.0, VariableType.AUXILIARY,
                                           equation_func=self._eq_consumo)

        self.gasto_implementacao = SimVariable("Fluxo_Gasto_Implementacao", 0.0, VariableType.AUXILIARY,
                                               equation_func=self._eq_gasto_implementacao)

        self.competitividade = SimVariable("Indice_Competitividade", 1.0, VariableType.AUXILIARY,
                                           equation_func=self._eq_competitividade)

        # --- ARRECADAÇÃO ---
        self.icms_energia = SimVariable("Arrecadacao_ICMS_Energia", 0.0, VariableType.AUXILIARY,
                                        equation_func=self._eq_icms_energia)
        
        self.icms_producao = SimVariable("Arrecadacao_ICMS_Producao", 0.0, VariableType.AUXILIARY,
                                         equation_func=self._eq_icms_producao)
        
        self.icms_total = SimVariable("Arrecadacao_Total", 0.0, VariableType.AUXILIARY,
                                      equation_func=self._eq_icms_total)

    # --- EQUAÇÕES CORRIGIDAS ---
    # As correções foram feitas substituindo o 'Display Name' pelo 'Attribute Name'

    @staticmethod
    def _eq_gasto_implementacao(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.capital_investimento e vars.FORCA_POLITICA
        taxa_execucao = 0.1 + (0.2 * vars.FORCA_POLITICA.v)
        return vars.capital_investimento.v * taxa_execucao

    @staticmethod
    def _eq_capital_investimento(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.producao, vars.FORCA_POLITICA e vars.gasto_implementacao
        reinvestimento = vars.producao.v * 0.005 
        aporte_governo = 500_000 * vars.FORCA_POLITICA.v 
        saida_gasto = vars.gasto_implementacao.v
        return (reinvestimento + aporte_governo) - saida_gasto

    @staticmethod
    def _eq_estoque_eficiencia(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.limite_eficiencia, vars.eficiencia, vars.sensib_invest_eff, vars.gasto_implementacao
        gap_tecnologico = vars.limite_eficiencia.v - vars.eficiencia.v
        ganho = gap_tecnologico * vars.sensib_invest_eff.v * (vars.gasto_implementacao.v / 100_000)
        depreciacao = vars.eficiencia.v * 0.01 
        return ganho - depreciacao

    @staticmethod
    def _eq_consumo(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.theta_intensidade, vars.producao, vars.eficiencia, vars.fator_rebote
        consumo_teorico = vars.theta_intensidade.v * vars.producao.v
        fator_eficiencia = (1 - vars.eficiencia.v)
        rebote = vars.fator_rebote.v * (consumo_teorico * vars.eficiencia.v)
        return (consumo_teorico * fator_eficiencia) + rebote

    @staticmethod
    def _eq_competitividade(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.eficiencia
        return 1.0 + (vars.eficiencia.v * 0.5)

    @staticmethod
    def _eq_producao(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.competitividade, vars.sensib_comp_prod, vars.producao
        crescimento_vegetativo = 0.002 
        impulso_competitividade = (vars.competitividade.v - 1.0) * vars.sensib_comp_prod.v
        return vars.producao.v * (crescimento_vegetativo + impulso_competitividade)

    @staticmethod
    def _eq_icms_energia(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.consumo_energia, vars.TARIFA_R_MWh, vars.ICMS_ALIQUOTA
        return vars.consumo_energia.v * vars.TARIFA_R_MWh.v * vars.ICMS_ALIQUOTA.v

    @staticmethod
    def _eq_icms_producao(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.producao
        return vars.producao.v * 0.12 

    @staticmethod
    def _eq_icms_total(self_var: SimVariable, vars: Any) -> float:
        # Acessa vars.icms_energia, vars.icms_producao
        return vars.icms_energia.v + vars.icms_producao.v