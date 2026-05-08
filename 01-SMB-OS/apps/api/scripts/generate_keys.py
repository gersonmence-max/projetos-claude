"""Run once to generate RS256 key pair. Output goes into .env"""


def main() -> None:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    # Output as single-line \n-escaped values safe for Docker/CI .env files
    private_oneline = private_pem.replace("\n", "\\n")
    public_oneline = public_pem.replace("\n", "\\n")

    print("# WARNING: generate fresh keys for EVERY environment. Never share .env across envs.")
    print(f'JWT_PRIVATE_KEY="{private_oneline}"')
    print(f'JWT_PUBLIC_KEY="{public_oneline}"')


if __name__ == "__main__":
    main()
