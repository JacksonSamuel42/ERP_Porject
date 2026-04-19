from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_production_keys():
    # Gerar chave privada RSA de 2048 bits (Padrão seguro)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Exportar Chave Privada (Formato PKCS8)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Exportar Chave Pública
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Guardar em ficheiros
    with open('private_key.pem', 'wb') as f:
        f.write(private_pem)

    with open('public_key.pem', 'wb') as f:
        f.write(public_pem)

    print('✅ Chaves geradas com sucesso!')
    print("⚠️  AVISO: Mantenha o 'private_key.pem' em segredo absoluto.")
    print("ℹ️  O 'public_key.pem' deve ser distribuído com o seu App Desktop.")
