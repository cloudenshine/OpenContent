"""Only mother-related evidence is eligible for this trusted built-in pack."""
from opencontent.workbench import target_context


def select(objects, mother):
    return target_context(objects, mother)
