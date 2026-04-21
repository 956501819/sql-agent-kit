import json
from pathlib import Path


class FewShotStore:
    """
    Few-shot 示例管理器
    存储"问题 → SQL"示例对，注入 Prompt 提升准确率
    持久化到 JSON 文件，方便直接编辑添加
    """

    def __init__(self, store_path: str = "./data/fewshot.json"):
        self._path = Path(store_path)
        self._examples: list[dict] = []
        self._load()

    def _load(self):
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                self._examples = json.load(f)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._examples, f, ensure_ascii=False, indent=2)

    def add(self, question: str, sql: str, tags: list[str] = None):
        """添加一条示例"""
        self._examples.append({
            "question": question,
            "sql": sql,
            "tags": tags or [],
        })
        self._save()

    def remove(self, index: int):
        """按序号删除"""
        self._examples.pop(index)
        self._save()

    def list_all(self) -> list[dict]:
        return list(self._examples)
