"""Export trained models to ONNX format for optimization."""

import torch
import argparse
import os
import logging

from src.models.teacher import RealSmolVLAModel
from src.models.student import StudentModel

logger = logging.getLogger(__name__)


def export_to_onnx(model, save_path, input_shape=(1, 2048)):
    model.eval()
    dummy_input = torch.randn(*input_shape)
    
    torch.onnx.export(
        model,
        dummy_input,
        save_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    logger.info(f"Model exported to {save_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', type=str, required=True)
    parser.add_argument('--output_dir', type=str, default='onnx_models')
    parser.add_argument('--ratio', type=float, default=0.5)
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    teacher = RealSmolVLAModel()
    student = StudentModel(ratio=args.ratio)
    
    try:
        checkpoint = torch.load(args.model_path, map_location='cpu')
        if 'student_state_dict' in checkpoint:
            student.load_state_dict(checkpoint['student_state_dict'])
        elif 'model_state_dict' in checkpoint:
            student.load_state_dict(checkpoint['model_state_dict'])
    except Exception as e:
        logger.warning(f"Could not load checkpoint: {e}")
    
    teacher_path = os.path.join(args.output_dir, 'teacher.onnx')
    student_path = os.path.join(args.output_dir, 'student.onnx')
    
    export_to_onnx(teacher, teacher_path)
    export_to_onnx(student, student_path)
    
    logger.info("ONNX export completed")


if __name__ == '__main__':
    main()