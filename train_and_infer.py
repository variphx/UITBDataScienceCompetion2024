import json
from schema import dataset, trainer, model
import torch
from torch import nn
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader
from torch.nn import functional as F
from torchvision.transforms.v2 import Compose, ToImage, ToDtype
from torchmetrics.classification import MulticlassF1Score
from bitsandbytes.optim import AdamW8bit
from tqdm import tqdm

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

image_transforms = Compose([ToImage(), ToDtype(torch.float32, scale=False)])
class_names = ["not-sarcasm", "image-sarcasm", "text-sarcasm", "multi-sarcasm"]

text_tokenizer = trainer.text_tokenizer
image_processor = trainer.image_processor

train_dataset = dataset.VimmsdDataset(
    data_file="/kaggle/input/vimmsd-uit2024/vimmsd-train.json",
    images_dir="/kaggle/input/vimmsd-uit2024/training-images/train-images",
    class_names=class_names,
    task="train",
)
train_dataloader = DataLoader(
    train_dataset, batch_size=64, collate_fn=trainer.train_collate_fn
)
vimmsd_model = model.VimmsdModel(device=device).to(device)
vimmsd_model(**(next(iter(train_dataloader))["features"]))

epochs = 8
optimizer = AdamW8bit(vimmsd_model.parameters(), 5e-5)
scheduler = lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=epochs * len(train_dataloader)
)
f1_metric = MulticlassF1Score(num_classes=4).to(device=device)
progress_bar = tqdm(range(epochs * len(train_dataloader)))
for epoch in range(epochs):
    for step, batch in enumerate(train_dataloader):
        optimizer.zero_grad()
        features, targets = batch["features"], batch["target"]
        targets = torch.as_tensor(targets, device=device)
        logits = vimmsd_model(**features)
        loss = F.cross_entropy(logits, targets)
        loss.backward()
        nn.utils.clip_grad_norm_(vimmsd_model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        f1_score = f1_metric(F.softmax(logits, dim=1), targets)
        progress_bar.set_description(f"loss={loss.item():.4f} f1={f1_score:.4f}")
        progress_bar.update(1)

torch.save(vimmsd_model.state_dict(), "/kaggle/working/model.pth")

infer_dataset = dataset.VimmsdDataset(
    data_file="/kaggle/input/vimmsd-uit2024/vimmsd-public-test.json",
    images_dir="/kaggle/input/vimmsd-uit2024/public-test-images/dev-images",
    class_names=class_names,
    task="infer",
)
infer_dataloader = DataLoader(
    infer_dataset, batch_size=1, collate_fn=trainer.infer_collate_fn
)

results = {}
vimmsd_model.eval()
for id, batch in (progress_bar := tqdm(enumerate(infer_dataloader), desc="infer")):
    features = batch["features"]
    logits = vimmsd_model(**features)
    predictions = F.softmax(logits, dim=1).argmax(dim=1)
    label = class_names[predictions[0]]
    progress_bar.set_postfix({f"id={id}", f"label={label}"})
    results[str(id)] = label

results = {
    "results": results,
    "phase": "dev",
}

with open("/kaggle/working/results.json", "w") as f:
    json.dump(results, f, indent=2)
