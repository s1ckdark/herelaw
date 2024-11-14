import torch
from transformers import pipeline, AutoTokenizer

model_id = "meta-llama/Llama-3.2-1B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Set the chat template
tokenizer.chat_template = "{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"

pipe = pipeline(
    "text-generation",
    model=model_id,
    tokenizer=tokenizer,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device=0 if torch.cuda.is_available() else -1
)

terminators = [
    pipe.tokenizer.eos_token_id,
    pipe.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
]


messages = [
    {"role": "system", "content": "You are a chatbot who always responds in korean"},
    {"role": "user", "content": "한국의 수도는 어디야?"},
]
outputs = pipe(
    messages,
    max_new_tokens=256,
    eos_token_id=terminators,
    do_sample=True,
    temperature=0.6,
    top_p=0.9,
    return_full_text=False,
)

assistant_response = outputs[0]["generated_text"]
print(assistant_response)
