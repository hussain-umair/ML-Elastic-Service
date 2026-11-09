import torch
from torchvision.models import resnet18, ResNet18_Weights
from torchvision import transforms

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

WEIGHTS = ResNet18_Weights.DEFAULT
MODEL = resnet18(weights=WEIGHTS)

class ModelInference:
    """A class to handle image preprocessing and inference using a pre-trained ResNet-18 model."""

    def __init__(self):
        self.image = None
        self.weights = WEIGHTS
        self.model = MODEL

    def transform_image(self, image):
        """Preprocess the input image for the ResNet-18 model."""

        self.image = image
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

        tensor = transform(image).unsqueeze(0)
        return tensor

    def predict(self, image_tensor):
        """Make a prediction on the preprocessed image."""
        
        preprocessed_image = image_tensor
        self.model.eval()
        
        prediction = self.model(preprocessed_image).squeeze(0).softmax(0)
        class_id = prediction.argmax().item()
        score = prediction[class_id].item()
        category_name = self.weights.meta["categories"][class_id]
        return f"{category_name} ({score:.2f})"
    