import enum


class Environment(str, enum.Enum):
    DEVELOPMENT = 'development'
    PRODUCTION = 'production'
