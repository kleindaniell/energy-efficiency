from sd_simulation import Simulation, SimVariable, VariableType, InfluenceMode
from typing import Dict

def create_fapergs_rge_model() -> Dict[str, SimVariable]:
    """
    Creates the FAPERGS RGE system dynamics model.
    """
    
    # Parameters
    params = {
        "TARIFA_R$/MWh": 650,
        "ICMS_TAU": 0.25,
        "theta1": 0.0008,
        "eta": 0.3,
        "rebote_frac": 0.1,
        "k_eff_inv": 0.0008,
        "k_eff_sge": 0.03,
        "k_eff_cap": 0.01,
        "k_eff_bar": 0.02,
        "k_gd_inv": 0.001,
        "k_gd_pol": 0.015,
        "theta_en_cost": 1,
        "theta_ineff": 60000,
        "theta_prod_comp": 600000,
        "theta_prod_cost": 0.08,
        "k_info_cap": 0.4,
        "k_info_pol": 0.25,
        "k_info_bar": 0.15,
        "k_bar_pol": 0.45,
        "k_bar_info": 0.35,
        "k_bar_cred": 0.35,
        "k_cred_green": 0.55,
        "k_cred_pol": 0.25,
        "beta_ICMS_EE": 0.12,
        "delta_ICMS_insumos": 0.018,
        "k_comp_eff": 3,
        "k_comp_cost": 5e-8,
        "POLITICAS": 0.55,
        "FIN_GREEN": 0.65,
    }

    # Variables
    variables = {
        # Stocks
        "V03_Eficiencia": SimVariable("Eficiência (0–1)", 0.25, VariableType.STOCK),
        "V04_Investimento_EE": SimVariable("Investimento EE (R$/mês)", 3000000, VariableType.STOCK),
        "V09_Producao": SimVariable("Produção (R$/mês)", 450000000, VariableType.STOCK),

        # Constants
        "V02_Tarifa": SimVariable("Tarifa (R$/MWh)", params["TARIFA_R$/MWh"], VariableType.CONSTANT),
        "V14_Politicas": SimVariable("Políticas (0–1)", params["POLITICAS"], VariableType.CONSTANT),
        "V22_Financiamento_Verde": SimVariable("Financiamento Verde (0–1)", params["FIN_GREEN"], VariableType.CONSTANT),

        # Auxiliaries
        "V01_Consumo": SimVariable("Consumo (MWh/mês)", 0, VariableType.AUXILIARY),
        "V05_Gestao_de_Energia": SimVariable("Gestão de Energia (0–1)", 0, VariableType.AUXILIARY),
        "V06_Barreiras": SimVariable("Barreiras (0–1)", 1, VariableType.AUXILIARY),
        "V07_Custos_Operacionais": SimVariable("Custos Operacionais (R$/mês)", params["theta_ineff"], VariableType.AUXILIARY),
        "V08_Informacao": SimVariable("Informação (0–1)", 0.4, VariableType.AUXILIARY),
        "V10_Credito": SimVariable("Crédito (0–1)", 0, VariableType.AUXILIARY),
        "V11_Competitividade": SimVariable("Competitividade (0–1)", 0, VariableType.AUXILIARY),
        "V16_Capacitacao": SimVariable("Capacitação (0–1)", 0, VariableType.AUXILIARY),
        "V17_Autogeracao": SimVariable("Autogeração (MWh/mês)", 0, VariableType.AUXILIARY),
        "V18_ICMS_Energia": SimVariable("ICMS Energia (R$/mês)", 0, VariableType.AUXILIARY),
        "V20_ICMS_EE": SimVariable("ICMS EE (R$/mês)", 0, VariableType.AUXILIARY),
        "V21_ICMS_Total": SimVariable("ICMS Total (R$/mês)", 0, VariableType.AUXILIARY),
        "V29_ICMS_Insumos": SimVariable("ICMS Insumos (R$/mês)", 0, VariableType.AUXILIARY),
    }

    # Define influences based on the formulas
    # V01 = θ1·V09·(1 − η·V03) − V17 + rebote_frac·η·V03·θ1·V09
    variables["V01_Consumo"].add_influence(variables["V09_Producao"], weight=params["theta1"])
    variables["V01_Consumo"].add_influence(variables["V03_Eficiencia"], weight=-params["theta1"] * params["eta"])
    variables["V01_Consumo"].add_influence(variables["V17_Autogeracao"], weight=-1)
    variables["V01_Consumo"].add_influence(variables["V03_Eficiencia"], weight=params["rebote_frac"] * params["eta"] * params["theta1"])

    # dV03/dt = k_eff_inv·V04 + k_eff_sge·V05 + k_eff_cap·V16 − k_eff_bar·V06
    variables["V03_Eficiencia"].add_influence(variables["V04_Investimento_EE"], weight=params["k_eff_inv"])
    variables["V03_Eficiencia"].add_influence(variables["V05_Gestao_de_Energia"], weight=params["k_eff_sge"])
    variables["V03_Eficiencia"].add_influence(variables["V16_Capacitacao"], weight=params["k_eff_cap"])
    variables["V03_Eficiencia"].add_influence(variables["V06_Barreiras"], weight=-params["k_eff_bar"])

    # dV04/dt = 5e6·V10 + 1.5e6·V14 + 2.5e6·V08
    variables["V04_Investimento_EE"].add_influence(variables["V10_Credito"], weight=5e6)
    variables["V04_Investimento_EE"].add_influence(variables["V14_Politicas"], weight=1.5e6)
    variables["V04_Investimento_EE"].add_influence(variables["V08_Informacao"], weight=2.5e6)

    # V05 = k_eff_sge·V14 + k_eff_cap·V16
    variables["V05_Gestao_de_Energia"].add_influence(variables["V14_Politicas"], weight=params["k_eff_sge"])
    variables["V05_Gestao_de_Energia"].add_influence(variables["V16_Capacitacao"], weight=params["k_eff_cap"])

    # V06 = 1 − (k_bar_pol·V14 + k_bar_info·V08 + k_bar_cred·V10)
    variables["V06_Barreiras"].add_influence(variables["V14_Politicas"], weight=-params["k_bar_pol"])
    variables["V06_Barreiras"].add_influence(variables["V08_Informacao"], weight=-params["k_bar_info"])
    variables["V06_Barreiras"].add_influence(variables["V10_Credito"], weight=-params["k_bar_cred"])

    # V07 = θ_en_cost·V01·V02 + θ_ineff·(1 − V03)
    variables["V07_Custos_Operacionais"].add_influence(variables["V01_Consumo"], weight=params["theta_en_cost"] * variables["V02_Tarifa"].value)
    variables["V07_Custos_Operacionais"].add_influence(variables["V03_Eficiencia"], weight=-params["theta_ineff"])

    # V08 = k_info_cap·V16 + k_info_pol·V14 − k_info_bar·V06 + 0.4
    variables["V08_Informacao"].add_influence(variables["V16_Capacitacao"], weight=params["k_info_cap"])
    variables["V08_Informacao"].add_influence(variables["V14_Politicas"], weight=params["k_info_pol"])
    variables["V08_Informacao"].add_influence(variables["V06_Barreiras"], weight=-params["k_info_bar"])

    # dV09/dt = θ_prod_comp·V11 − θ_prod_cost·V07
    variables["V09_Producao"].add_influence(variables["V11_Competitividade"], weight=params["theta_prod_comp"])
    variables["V09_Producao"].add_influence(variables["V07_Custos_Operacionais"], weight=-params["theta_prod_cost"])

    # V10 = k_cred_green·V22 + k_cred_pol·V14
    variables["V10_Credito"].add_influence(variables["V22_Financiamento_Verde"], weight=params["k_cred_green"])
    variables["V10_Credito"].add_influence(variables["V14_Politicas"], weight=params["k_cred_pol"])

    # V11 = 1 / (1 + exp(−(k_comp_eff·V03 − k_comp_cost·V07))) -> Logistic function
    variables["V11_Competitividade"].add_influence(variables["V03_Eficiencia"], weight=params["k_comp_eff"], mode=InfluenceMode.LOGISTIC)
    variables["V11_Competitividade"].add_influence(variables["V07_Custos_Operacionais"], weight=-params["k_comp_cost"], mode=InfluenceMode.LOGISTIC)

    # V16 = V14
    variables["V16_Capacitacao"].add_influence(variables["V14_Politicas"], weight=1)

    # V17 = k_gd_inv·V04 + k_gd_pol·V14·800
    variables["V17_Autogeracao"].add_influence(variables["V04_Investimento_EE"], weight=params["k_gd_inv"])
    variables["V17_Autogeracao"].add_influence(variables["V14_Politicas"], weight=params["k_gd_pol"] * 800)

    # V18 = τ·V02·V01
    variables["V18_ICMS_Energia"].add_influence(variables["V01_Consumo"], weight=params["ICMS_TAU"] * variables["V02_Tarifa"].value)

    # V20 = β_ICMS_EE·V04
    variables["V20_ICMS_EE"].add_influence(variables["V04_Investimento_EE"], weight=params["beta_ICMS_EE"])

    # V21 = V18 + V20 + V29
    variables["V21_ICMS_Total"].add_influence(variables["V18_ICMS_Energia"], weight=1)
    variables["V21_ICMS_Total"].add_influence(variables["V20_ICMS_EE"], weight=1)
    variables["V21_ICMS_Total"].add_influence(variables["V29_ICMS_Insumos"], weight=1)

    # V29 = δ_ICMS_insumos·V09
    variables["V29_ICMS_Insumos"].add_influence(variables["V09_Producao"], weight=params["delta_ICMS_insumos"])

    return variables

if __name__ == '__main__':
    # This block can be used for testing the model directly
    model = create_fapergs_rge_model()
    print(f"Model created with {len(model)} variables.")
