from .colour_relation_models import Mamajek2008

__all__ = []

def Mamajek_rotation_rate(BV0, age, extrapolate=False):
    return Mamajek2008.rotation_rate(BV0, age, extrapolate=extrapolate)
Mamajek_rotation_rate.__doc__ = (Mamajek2008._rotation_rate.__doc__)
__all__ += ['Mamajek_rotation_rate']
