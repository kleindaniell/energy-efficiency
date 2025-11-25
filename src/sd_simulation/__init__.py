from .engine import (
    Simulation,
    SimVariable,
    VariableType,
    MockSimVariable, # Adicionado para o grafo de dependências
)

# from .models import ( # Comentado, pois o modelo antigo pode não ser compatível
#     fapergs_rge_model
# )

__all__ = [
    "Simulation",
    "SimVariable",
    "VariableType",
    "MockSimVariable",
]
