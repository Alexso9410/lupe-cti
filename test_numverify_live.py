from centinela.enrichment.numverify import NumVerifyPlugin
from centinela.models import IOC, IOCType
import httpx
import asyncio

async def main():
    # Crear IOC con el número de prueba
    ioc = IOC(
        value="+54 9 2954 000000",
        type=IOCType.phone
    )

    # Leer la API key del .env
    try:
        with open(".env", "r", encoding="utf-8") as f:
            env_content = f.read()

        api_key = None
        for line in env_content.splitlines():
            if line.startswith("CENTINELA_NUMVERIFY_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"')
                break

        if not api_key:
            print("ERROR: No se encontró la variable CENTINELA_NUMVERIFY_KEY en .env")
            return

    except FileNotFoundError:
        print("ERROR: No se encontró el archivo .env")
        return

    # Crear cliente y ejecutar el plugin
    async with httpx.AsyncClient() as client:
        plugin = NumVerifyPlugin(api_key)

        print("Ejecutando NumVerifyPlugin con número: +54 9 2954 000000...")
        print("-" * 50)

        try:
            result = await plugin.enrich(ioc, client)

            if result:
                print(f"\nResultado exitoso:")
                print(f"Válido: {result.raw_data.get('valid', 'N/A')}")
                print(f"País: {result.raw_data.get('country_name', 'N/A')}")
                print(f"Operador: {result.raw_data.get('carrier', 'N/A')}")
                print(f"Tipo de línea: {result.raw_data.get('line_type', 'N/A')}")
                print(f"Formato internacional: {result.raw_data.get('international_format', 'N/A')}")
                print(f"Resumen: {result.summary}")
                print(f"Severidad: {result.severity}")

                # Mostrar datos completos para debugging
                print(f"\nDatos completos del API:")
                for key, value in result.raw_data.items():
                    print(f"  {key}: {value}")

            else:
                print("Resultado: None (puede ser API key inválida, límite excedido o error en la solicitud)")

        except Exception as e:
            print(f"ERROR durante la ejecución: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())