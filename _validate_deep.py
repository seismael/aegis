import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from aegis.kernel.server import AegisKernel

async def main():
    kernel = AegisKernel()
    files = [
        "src/aegis/domain/evaluation/scorecard.py",
        "tests/test_scorecard.py"
    ]
    print(f"Validating files: {files}")
    result = await kernel.validate_architecture_compliance(files_modified=files)
    print("\nValidation Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
