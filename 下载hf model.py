from transformers import AutoModel, AutoTokenizer

model_name = "BAAI/ABCD-bge-small-zh-v1.5"

# 下载并缓存模型
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
