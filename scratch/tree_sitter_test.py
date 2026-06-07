import asyncio
from pathlib import Path
from aegis.kernel.server import AegisKernel

async def main():
    root = "c:/dev/projects/aegis"
    kernel = AegisKernel(workspace_root=root)
    
    target_file = Path(root) / "scratch" / "query_service.py"
    target_file.write_text("""
class QueryService:
    def get_user_data(self, user_id):
        self.last_accessed = user_id  # Violation: assignment inside 'get_' method
        return {"id": user_id}
""", encoding="utf-8")

    res = await kernel.check_architecture(["scratch/query_service.py"])
    with open("scratch/ts_output.txt", "w", encoding="utf-8") as f:
        f.write(res)

if __name__ == "__main__":
    asyncio.run(main())
