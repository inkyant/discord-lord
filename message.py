
from unsloth import FastLanguageModel

prompt = """Below is a snippet of an online text conversation on Discord. The text before the user's response is given. Complete the user's response to the text message.

### Previous Message:
{}

### Response:
{}"""


model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="lora",  # folder name with saved safetensors, etc.
    max_seq_length=2048,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)  # Enable native 2x faster inference


inputs = tokenizer(
    [
        prompt.format(
            "how?",  # input
            "",  # output - leave this blank for generation!
        )
    ],
    return_tensors="pt",
).to("cuda")

outputs = model.generate(**inputs, max_new_tokens=64, use_cache=True)
generated = tokenizer.batch_decode(outputs)

print(generated)