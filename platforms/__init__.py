from .linkedin import LinkedInGenerator
from .facebook import FacebookGenerator
from .instagram import InstagramGenerator

REGISTRY = {
    "linkedin": LinkedInGenerator,
    "facebook": FacebookGenerator,
    "instagram": InstagramGenerator,
}
