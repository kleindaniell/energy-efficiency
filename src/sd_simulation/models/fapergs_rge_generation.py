from ..engine import SimVariable, VariableType

class FapergsRGEBaseModel:
    """
    Modelo de Dinâmica de Sistemas para PMEs Industriais (FAPERGS/RGE).
    Integra: 
    1. Crescimento Logístico de Produção (Limites de Mercado)
    2. Delay de Informação na Competitividade
    3. Estratégia Dupla: Eficiência Energética + Microgeração Distribuída (MGD)
    """
    def __init__(self, consumo_medio_inicial=113, producao_inicial=450_000_000):
        
        THETA_CALIBRADO = consumo_medio_inicial / producao_inicial

        # --- PARÂMETROS GERAIS ---
        self.TARIFA_R_MWh = SimVariable("Tarifa_Energia", 650.0, VariableType.CONSTANT)
        self.ICMS_ALIQUOTA = SimVariable("Aliquota_ICMS", 0.17, VariableType.CONSTANT)
        self.FORCA_POLITICA = SimVariable("Forca_Politica_Publica", 0, VariableType.CONSTANT)
        
        # Limite físico do mercado para a Curva Logística
        self.CAPACIDADE_MAXIMA = SimVariable("Capacidade_Maxima_Mercado", 500_000_000.0, VariableType.CONSTANT)
        
        # --- PARÂMETROS DE TEMPO (DELAYS) ---
        # Tempo para o mercado perceber a competitividade
        self.TEMPO_RESPOSTA_MERCADO = SimVariable("Tempo_Resposta_Mercado", 12.0, VariableType.CONSTANT)
        # Tempo para executar os projetos (gastar o capital acumulado)
        self.TEMPO_IMPLEMENTACAO = SimVariable("Tempo_Implementacao_Projetos", 10.0, VariableType.CONSTANT) 

        # --- PARÂMETROS DE ESTRATÉGIA (RDM) ---
        # Switch: 0.0 = Apenas Eficiência (Cenário Base) | 1.0 = Com Geração (Cenário MGD)
        self.SWITCH_GERACAO = SimVariable("Switch_Ativar_Geracao", 1.0, VariableType.CONSTANT)
        
        # Alocação: 40% do dinheiro vai para painéis solares, 60% para máquinas eficientes
        self.PCT_ALOCACAO_GERACAO = SimVariable("Pct_Alocacao_Capex_Geracao", 0.4, VariableType.CONSTANT)
        
        # Produtividade: Quantos MWh/ano gera R$ 1,00 investido em solar (ex: R$ 4000/kWp -> ~0.00035 MWh/BRL)
        # Valor calibrado para exemplo:
        self.PRODUTIVIDADE_GERACAO = SimVariable("Produtividade_Investimento_MWh_BRL", 0.0002, VariableType.CONSTANT)

        # --- PARÂMETROS TÉCNICOS ---
        # Intensidade inicial (Consumo / Produção)
        self.theta_intensidade = SimVariable("Intensidade_Energetica_Inicial", THETA_CALIBRADO, VariableType.CONSTANT)
        self.limite_eficiencia = SimVariable("Limite_Tecnico_Eficiencia", 0.60, VariableType.CONSTANT)
        
        # Parâmetros financeiros de investimento
        self.TAXA_REINVESTIMENTO = SimVariable("Pct_Reinvestimento_Faturamento", 0.005, VariableType.CONSTANT)
        self.CAPITAL_SATURACAO = SimVariable("Capital_Saturacao_Marginal", 1_000_000.0, VariableType.CONSTANT)
        self.CUSTO_EFICIENCIA = SimVariable("Custo_Para_Ganho_Eficiencia", 100_000.0, VariableType.CONSTANT)

        # Sensibilidades do sistema
        self.sensib_invest_eff = SimVariable("Sensib_Invest_Eficiencia", 0.0005, VariableType.CONSTANT)
        self.sensib_comp_prod = SimVariable("Sensib_Competitividade_Producao", 0.02, VariableType.CONSTANT)
        self.fator_rebote = SimVariable("Fator_Rebote", 0.15, VariableType.CONSTANT)

        # --- ESTOQUES (STOCKS) ---
        
        # 1. Estoque de Eficiência Técnica (adimensional, 0 a 60%)
        self.eficiencia = SimVariable("Estoque_Eficiencia", 0.10, VariableType.STOCK,
                                      min_value=0.0, max_value=0.60,
                                      equation_func=self._eq_estoque_eficiencia)

        # 2. Estoque de Capacidade de Geração (Valor investido em ativos de geração - R$)
        # [NOVO] Representa o parque instalado de MGD
        self.capacidade_geracao = SimVariable("Capacidade_Instalada_MGD_BRL", 0.0, VariableType.STOCK,
                                              equation_func=self._eq_capacidade_geracao)

        # 3. Fundo de Capital para Investimentos (R$)
        self.capital_investimento = SimVariable("Capital_Investimento_EE", 0.0, VariableType.STOCK,
                                                equation_func=self._eq_capital_investimento)

        # 4. Produção Industrial (R$/mês)
        self.producao = SimVariable("Producao_Industrial", producao_inicial, VariableType.STOCK,
                                    equation_func=self._eq_producao)

        # 5. Competitividade Percebida (Index) - Com Delay
        self.competitividade = SimVariable("Indice_Competitividade", 1.0, VariableType.STOCK,
                                           equation_func=self._eq_competitividade_stock_flow)

        # --- VARIÁVEIS AUXILIARES ---
        
        self.competitividade_alvo = SimVariable("Competitividade_Potencial_Alvo", 1.0, VariableType.AUXILIARY,
                                                equation_func=self._eq_competitividade_alvo)

        # Consumo Bruto (baseado na física da fábrica)
        self.consumo_energia = SimVariable("Consumo_Energia_Bruto", 0.0, VariableType.AUXILIARY,
                                           equation_func=self._eq_consumo_bruto)

        # [NOVO] Geração de Energia (MWh)
        self.energia_gerada = SimVariable("Energia_Gerada_MGD", 0.0, VariableType.AUXILIARY,
                                          equation_func=self._eq_energia_gerada)

        # [NOVO] Consumo Líquido (Base para fatura e impostos)
        self.consumo_liquido = SimVariable("Consumo_Liquido_Rede", 0.0, VariableType.AUXILIARY,
                                           equation_func=self._eq_consumo_liquido)

        self.gasto_implementacao = SimVariable("Fluxo_Gasto_Implementacao", 0.0, VariableType.AUXILIARY,
                                               equation_func=self._eq_gasto_implementacao)

        # --- ARRECADAÇÃO (Fiscal) ---
        self.icms_energia = SimVariable("Arrecadacao_ICMS_Energia", 0.0, VariableType.AUXILIARY,
                                        equation_func=self._eq_icms_energia)
        self.icms_producao = SimVariable("Arrecadacao_ICMS_Producao", 0.0, VariableType.AUXILIARY,
                                         equation_func=self._eq_icms_producao)
        self.icms_total = SimVariable("Arrecadacao_Total", 0.0, VariableType.AUXILIARY,
                                      equation_func=self._eq_icms_total)

    # --- EQUAÇÕES DO MODELO ---

    @staticmethod
    def _eq_gasto_implementacao(self_var: SimVariable, vars: Any) -> float:
        # Determina a velocidade com que o dinheiro sai do cofre para virar projeto real
        # A Força Política pode acelerar processos (reduzindo burocracia/tempo)
        fator_aceleracao = 1.0 + (0.5 * vars.FORCA_POLITICA.v)
        tempo_real = vars.TEMPO_IMPLEMENTACAO.v / fator_aceleracao
        return vars.capital_investimento.v / tempo_real

    @staticmethod
    def _eq_capital_investimento(self_var: SimVariable, vars: Any) -> float:
        # Fluxo de Entrada: Reinvestimento de parte da Produção
        reinvestimento_potencial = vars.producao.v * vars.TAXA_REINVESTIMENTO.v
        
        # Freio de Saturação: Se tem muito dinheiro parado, para de aportar
        fator_freio = 1 + (vars.capital_investimento.v / vars.CAPITAL_SATURACAO.v)
        reinvestimento_real = reinvestimento_potencial / fator_freio
        
        # Subsídios governamentais
        aporte_governo = 50_000 * vars.FORCA_POLITICA.v
        
        # Saída: Gasto efetivo em projetos
        saida_gasto = vars.gasto_implementacao.v
        
        return (reinvestimento_real + aporte_governo) - saida_gasto

    @staticmethod
    def _eq_estoque_eficiencia(self_var: SimVariable, vars: Any) -> float:
        # Define quanto do orçamento vai para eficiência vs geração
        pct_geracao = vars.PCT_ALOCACAO_GERACAO.v * vars.SWITCH_GERACAO.v
        orcamento_eficiencia = vars.gasto_implementacao.v * (1.0 - pct_geracao)
        
        # Ganho marginal de eficiência (diminui conforme se aproxima do limite técnico)
        gap_tecnologico = vars.limite_eficiencia.v - vars.eficiencia.v
        
        # Aumenta eficiência baseado no valor investido
        ganho = gap_tecnologico * vars.sensib_invest_eff.v * (orcamento_eficiencia / vars.CUSTO_EFICIENCIA.v)
        
        # Depreciação tecnológica (máquinas ficando obsoletas)
        depreciacao = vars.eficiencia.v * 0.01
        return ganho - depreciacao

    @staticmethod
    def _eq_capacidade_geracao(self_var: SimVariable, vars: Any) -> float:
        # [NOVO] Estoque de Ativos de Geração
        
        # Entrada: Parte do orçamento destinada à geração (se Switch estiver ligado)
        pct_geracao = vars.PCT_ALOCACAO_GERACAO.v * vars.SWITCH_GERACAO.v
        investimento_mgd = vars.gasto_implementacao.v * pct_geracao
        
        # Saída: Depreciação física dos painéis/inversores (ex: 4% ao ano)
        # Essencial para não crescer infinitamente
        depreciacao = vars.capacidade_geracao.v * 0.04 
        
        return investimento_mgd - depreciacao

    @staticmethod
    def _eq_energia_gerada(self_var: SimVariable, vars: Any) -> float:
        # [NOVO] Converte o estoque de ativos (R$) em energia física (MWh)
        # A produtividade depende da tecnologia (MWh/R$)
        return vars.capacidade_geracao.v * vars.PRODUTIVIDADE_GERACAO.v

    @staticmethod
    def _eq_consumo_bruto(self_var: SimVariable, vars: Any) -> float:
        # Consumo base da fábrica antes da geração própria
        consumo_teorico = vars.theta_intensidade.v * vars.producao.v
        fator_eficiencia = (1 - vars.eficiencia.v)
        # Efeito Rebote: Aumento de uso devido à percepção de eficiência
        rebote = vars.fator_rebote.v * (consumo_teorico * vars.eficiencia.v)
        return (consumo_teorico * fator_eficiencia) + rebote

    @staticmethod
    def _eq_consumo_liquido(self_var: SimVariable, vars: Any) -> float:
        # [NOVO] Consumo que será faturado pela concessionária
        # Net Metering: Abate a geração do consumo bruto
        saldo = vars.consumo_energia.v - vars.energia_gerada.v
        # Não permite consumo negativo (venda de excedente não modelada neste escopo fiscal)
        return max(0.0, saldo)

    @staticmethod
    def _eq_competitividade_alvo(self_var: SimVariable, vars: Any) -> float:
        # Define a competitividade potencial baseada na eficiência atual
        return 1.0 + (vars.eficiencia.v * 0.1)

    @staticmethod
    def _eq_competitividade_stock_flow(self_var: SimVariable, vars: Any) -> float:
        # Delay de informação de 1ª ordem: Ajusta a competitividade real em direção ao alvo
        alvo = vars.competitividade_alvo.v
        atual = vars.competitividade.v
        delay = vars.TEMPO_RESPOSTA_MERCADO.v
        return (alvo - atual) / delay

    @staticmethod
    def _eq_producao(self_var: SimVariable, vars: Any) -> float:
        # Taxa de crescimento composta
        taxa_base = 0.001
        impulso = (vars.competitividade.v - 1.0) * vars.sensib_comp_prod.v
        r = taxa_base + impulso
        
        # Crescimento Logístico com capacidade de suporte (K)
        P = vars.producao.v
        K = vars.CAPACIDADE_MAXIMA.v
        
        fluxo = r * P * (1 - (P / K))
        return max(0, fluxo) # Evita valores negativos

    @staticmethod
    def _eq_icms_energia(self_var: SimVariable, vars: Any) -> float:
        # [ATUALIZADO] O ICMS incide sobre o Consumo Líquido (após compensação da geração)
        return vars.consumo_liquido.v * vars.TARIFA_R_MWh.v * vars.ICMS_ALIQUOTA.v

    @staticmethod
    def _eq_icms_producao(self_var: SimVariable, vars: Any) -> float:
        return vars.producao.v * 0.12

    @staticmethod
    def _eq_icms_total(self_var: SimVariable, vars: Any) -> float:
        return vars.icms_energia.v + vars.icms_producao.v