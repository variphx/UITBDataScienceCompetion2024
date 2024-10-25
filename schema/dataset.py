import json as _json
import pathlib as _pathlib
from PIL import Image as _Image
from torch.utils.data import Dataset as _Dataset


class VimmsdDataset(_Dataset):
    def __init__(
        self,
        data_file: str,
        images_dir: str,
        class_names: list[str],
        task: str,
    ):
        super().__init__()
        assert task == "train" or task == "infer"

        self._task = task
        self._class_names = class_names
        self._label2id = {label: id for id, label in enumerate(self._class_names)}

        with open(data_file, "r") as f:
            self._data: dict[str, dict[str, str]] = _json.load(f)
        self._images_dir = _pathlib.PurePath(images_dir)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        item = self._data[str(index)]
        features = {
            "image": _Image.open(self._images_dir.joinpath(item["image"])).convert(
                "RGB"
            ),
            "text": item["caption"],
        }
        if self._task == "train":
            target = self._label2id[item["label"]]
            return {"features": features, "target": target}
        else:
            return {"features": features}
