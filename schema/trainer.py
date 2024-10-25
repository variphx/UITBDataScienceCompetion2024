import torch
from torchvision.transforms.v2 import Compose, ToImage, ToDtype
from transformers import AutoTokenizer, AutoImageProcessor

image_transforms = Compose([ToImage(), ToDtype(torch.float32, scale=False)])
text_tokenizer = AutoTokenizer.from_pretrained("uitnlp/CafeBERT")
image_processor = AutoImageProcessor.from_pretrained(
    "facebook/deit-base-distilled-patch16-224"
)


def train_collate_fn(batch):
    features = {
        "image": image_processor(
            images=[image_transforms(item["features"]["image"]) for item in batch],
            return_tensors="pt",
        ),
        "text": text_tokenizer(
            [item["features"]["text"] for item in batch],
            max_length=512,
            padding="max_length",
            truncation=True,
            add_special_tokens=True,
            return_tensors="pt",
        ),
    }
    targets = [item["target"] for item in batch]

    return {"features": features, "target": targets}


def infer_collate_fn(batch):
    features = {
        "image": image_processor(
            images=[image_transforms(item["features"]["image"]) for item in batch],
            return_tensors="pt",
        ),
        "text": text_tokenizer(
            [item["features"]["text"] for item in batch],
            max_length=512,
            padding="max_length",
            truncation=True,
            add_special_tokens=True,
            return_tensors="pt",
        ),
    }
    return {"features": features}
