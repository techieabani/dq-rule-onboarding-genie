import os
import sys
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
import json
import pynvml
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import login
from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("FINETUNE_WRAPPER")

# This looks for a .env file in the current directory or parents
#load_dotenv() 

# Huggingface token for model access
hf_token = os.getenv("HF_TOKEN")
login(token=hf_token)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ADAPTER_PATH = PROJECT_ROOT / "models" / "rule-extractor-adapter"
BASE_MODEL_ID = "google/gemma-2-2b-it"

class RuleExtractionModelWrapper:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        # PRE-CHECK: Is there enough VRAM?
        if not self._is_vram_available():
            logger.error("ABORTING: Insufficient VRAM or another model instance detected.")
            sys.exit(1)
        self._load_model()
    
    def _load_model(self):
        """Load model with 4-bit quantization on GPU"""
        logger.info("=" * 60)
        logger.info("Loading Model...")
        logger.info("=" * 60)
        
        if not ADAPTER_PATH.exists():
            raise FileNotFoundError(
                f"Adapter not found at {ADAPTER_PATH}\n"
            )
        
        # Verify GPU
        if not torch.cuda.is_available():
            raise RuntimeError("No GPU detected. This code requires CUDA.")
        
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"***GPU: {gpu_name}***")
        logger.info(f"***PyTorch: {torch.__version__}***")
        logger.info(f"***CUDA: {torch.version.cuda}***")
        
        # Load tokenizer
        logger.info(f"\nLoading tokenizer...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(ADAPTER_PATH))
            logger.info(f"Loaded from adapter")
        except Exception as e:
            logger.info(f"Loading from base model instead...")
            self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
        
        # Load base model with 4-bit quantization
        logger.info(f"\n Loading base model: {BASE_MODEL_ID}")
        logger.info(f" Using 4-bit quantization...")
        logger.info("Testing GPU access...")
        logger.info(f"CUDA Available: {torch.cuda.is_available()}")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        # Force the device map to specifically target GPU 0
        #device_map = {"": 0}
        self.model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
            attn_implementation="eager",
            low_cpu_mem_usage=True,
            #offload_folder="offload", # Safety catch
        )
        logger.info("Success! GPU is receiving data.")
        # Load LoRA adapter
        logger.info(f"\n Loading LoRA adapter...")
        self.model = PeftModel.from_pretrained(
            self.model, 
            str(ADAPTER_PATH),
            local_files_only=True
        )
        
        # Show memory usage
        vram = torch.cuda.memory_allocated() / 1024**3
        total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        
        logger.info("\n" + "=" * 60)
        logger.info("Model loaded successfully!")
        logger.info(f"GPU VRAM: {vram:.2f} GB / {total_vram:.2f} GB ({vram/total_vram*100:.1f}%)")
        logger.info("=" * 60)
    
    def generate(self, instruction: str, max_tokens=350, temperature=0.1) -> dict:
        """Generate rule JSON from instruction"""
        logger.info(f"Generating rule for instruction:\n{instruction}\n")
        messages = [{"role": "user", "content": f"Map to JSON: {instruction}"}]
        
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(
            input_text, 
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=True,
            )
        
        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"Fine Tune Model generated output:\n{result}\n")
        #Extract JSON
        start = result.find("{")
        end = result.rfind("}") + 1
        json_str = result[start:end] if start != -1 and end > start else result
        return json.loads(json_str)
    
    def _is_vram_available(self, threshold_mb=1200):
        """Checks if the GPU has enough free space to load a new 2.2GB model."""
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used_mb = info.used / 1024**2
            total_mb = info.total / 1024**2
            
            logger.info(f"Initial VRAM Check: {used_mb:.1f}MB used of {total_mb:.1f}MB")
            
            # If used VRAM is > 1.2GB, a Gemma model or ghost process is likely present
            if used_mb > threshold_mb:
                logger.warning(f"High VRAM usage detected ({used_mb:.1f}MB).")
                logger.warning("This usually means another process is already hosting the model.")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check VRAM: {e}")
            return True # Fallback to try loading anyway

rule_extraction_model_wrapper = RuleExtractionModelWrapper()