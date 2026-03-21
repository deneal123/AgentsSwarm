OpenAI-Compatible Server¶
vLLM provides an HTTP server that implements OpenAI's Completions API, Chat API, and more! This functionality lets you serve models and interact with them using an HTTP client.

In your terminal, you can install vLLM, then start the server with the vllm serve command. (You can also use our Docker image.)


vllm serve NousResearch/Meta-Llama-3-8B-Instruct \
  --dtype auto \
  --api-key token-abc123
To call the server, in your preferred text editor, create a script that uses an HTTP client. Include any messages that you want to send to the model. Then run that script. Below is an example script using the official OpenAI Python client.

Code
Tip

vLLM supports some parameters that are not supported by OpenAI, top_k for example. You can pass these parameters to vLLM using the OpenAI client in the extra_body parameter of your requests, i.e. extra_body={"top_k": 50} for top_k.

Important

By default, the server applies generation_config.json from the Hugging Face model repository if it exists. This means the default values of certain sampling parameters can be overridden by those recommended by the model creator.

To disable this behavior, please pass --generation-config vllm when launching the server.

Supported APIs¶
We currently support the following OpenAI APIs:

Completions API (/v1/completions)
Only applicable to text generation models.
Note: suffix parameter is not supported.
Responses API (/v1/responses)
Only applicable to text generation models.
Chat Completions API (/v1/chat/completions)
Only applicable to text generation models with a chat template.
Note: user parameter is ignored.
Note: Setting the parallel_tool_calls parameter to false ensures vLLM only returns zero or one tool call per request. Setting it to true (the default) allows returning more than one tool call per request. There is no guarantee more than one tool call will be returned if this is set to true, as that behavior is model dependent and not all models are designed to support parallel tool calls.
Embeddings API (/v1/embeddings)
Only applicable to embedding models.
Transcriptions API (/v1/audio/transcriptions)
Only applicable to Automatic Speech Recognition (ASR) models.
Translation API (/v1/audio/translations)
Only applicable to Automatic Speech Recognition (ASR) models.
Realtime API (/v1/realtime)
Only applicable to Automatic Speech Recognition (ASR) models.
In addition, we have the following custom APIs:

Tokenizer API (/tokenize, /detokenize)
Applicable to any model with a tokenizer.
pooling API (/pooling)
Applicable to all pooling models.
Classification API (/classify)
Only applicable to classification models.
Cohere Embed API (/v2/embed)
Compatible with Cohere's Embed API
Works with any embedding model, including multimodal models.
Score API (/score)
Applicable to score models.
Rerank API (/rerank, /v1/rerank, /v2/rerank)
Implements Jina AI's v1 rerank API
Also compatible with Cohere's v1 & v2 rerank APIs
Jina and Cohere's APIs are very similar; Jina's includes extra information in the rerank endpoint's response.
Chat Template¶
In order for the language model to support chat protocol, vLLM requires the model to include a chat template in its tokenizer configuration. The chat template is a Jinja2 template that specifies how roles, messages, and other chat-specific tokens are encoded in the input.

An example chat template for NousResearch/Meta-Llama-3-8B-Instruct can be found here

Some models do not provide a chat template even though they are instruction/chat fine-tuned. For those models, you can manually specify their chat template in the --chat-template parameter with the file path to the chat template, or the template in string form. Without a chat template, the server will not be able to process chat and all chat requests will error.


vllm serve <model> --chat-template ./path-to-chat-template.jinja
vLLM community provides a set of chat templates for popular models. You can find them under the  examples directory.

With the inclusion of multi-modal chat APIs, the OpenAI spec now accepts chat messages in a new format which specifies both a type and a text field. An example is provided below:


completion = client.chat.completions.create(
    model="NousResearch/Meta-Llama-3-8B-Instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Classify this sentiment: vLLM is wonderful!"},
            ],
        },
    ],
)
Most chat templates for LLMs expect the content field to be a string, but there are some newer models like meta-llama/Llama-Guard-3-1B that expect the content to be formatted according to the OpenAI schema in the request. vLLM provides best-effort support to detect this automatically, which is logged as a string like "Detected the chat template content format to be...", and internally converts incoming requests to match the detected format, which can be one of:

"string": A string.
Example: "Hello world"
"openai": A list of dictionaries, similar to OpenAI schema.
Example: [{"type": "text", "text": "Hello world!"}]
If the result is not what you expect, you can set the --chat-template-content-format CLI argument to override which format to use.

Extra Parameters¶
vLLM supports a set of parameters that are not part of the OpenAI API. In order to use them, you can pass them as extra parameters in the OpenAI client. Or directly merge them into the JSON payload if you are using HTTP call directly.


completion = client.chat.completions.create(
    model="NousResearch/Meta-Llama-3-8B-Instruct",
    messages=[
        {"role": "user", "content": "Classify this sentiment: vLLM is wonderful!"},
    ],
    extra_body={
        "structured_outputs": {"choice": ["positive", "negative"]},
    },
)
Extra HTTP Headers¶
Only X-Request-Id HTTP request header is supported for now. It can be enabled with --enable-request-id-headers.

Code
Offline API Documentation¶
The FastAPI /docs endpoint requires an internet connection by default. To enable offline access in air-gapped environments, use the --enable-offline-docs flag:


vllm serve NousResearch/Meta-Llama-3-8B-Instruct --enable-offline-docs
API Reference¶
Completions API¶
Our Completions API is compatible with OpenAI's Completions API; you can use the official OpenAI Python client to interact with it.

Code example:  examples/basic/online_serving/openai_completion_client.py

Extra parameters¶
The following sampling parameters are supported.

Code
The following extra parameters are supported:

Code
Chat API¶
Our Chat API is compatible with OpenAI's Chat Completions API; you can use the official OpenAI Python client to interact with it.

We support both Vision- and Audio-related parameters; see our Multimodal Inputs guide for more information.

Note: image_url.detail parameter is not supported.
Code example:  examples/basic/online_serving/openai_chat_completion_client.py

Extra parameters¶
The following sampling parameters are supported.

Code
The following extra parameters are supported:

Code
Responses API¶
Our Responses API is compatible with OpenAI's Responses API; you can use the official OpenAI Python client to interact with it.

Code example:  examples/online_serving/openai_responses_client_with_tools.py

Extra parameters¶
The following extra parameters in the request object are supported:

Code
The following extra parameters in the response object are supported:

Code
Transcriptions API¶
Our Transcriptions API is compatible with OpenAI's Transcriptions API; you can use the official OpenAI Python client to interact with it.

Note

To use the Transcriptions API, please install with extra audio dependencies using pip install vllm[audio].

Code example:  examples/online_serving/openai_transcription_client.py

NOTE: beam search is currently supported in the transcriptions endpoint for encoder-decoder multimodal models, e.g., whisper, but highly inefficient as work for handling the encoder/decoder cache is actively ongoing. This is an active point of ongoing optimization and will be handled properly in the very near future.

API Enforced Limits¶
Set the maximum audio file size (in MB) that VLLM will accept, via the VLLM_MAX_AUDIO_CLIP_FILESIZE_MB environment variable. Default is 25 MB.

Uploading Audio Files¶
The Transcriptions API supports uploading audio files in various formats including FLAC, MP3, MP4, MPEG, MPGA, M4A, OGG, WAV, and WEBM.

Using OpenAI Python Client:

Code
Using curl with multipart/form-data:

Code
Supported Parameters:

file: The audio file to transcribe (required)
model: The model to use for transcription (required)
language: The language code (e.g., "en", "zh") (optional)
prompt: Optional text to guide the transcription style (optional)
response_format: Format of the response ("json", "text") (optional)
temperature: Sampling temperature between 0 and 1 (optional)
For the complete list of supported parameters including sampling parameters and vLLM extensions, see the protocol definitions.

Response Format:

For verbose_json response format:

Code
Currently “verbose_json” response format doesn’t support no_speech_prob.

Extra Parameters¶
The following sampling parameters are supported.

Code
The following extra parameters are supported:

Code
Translations API¶
Our Translation API is compatible with OpenAI's Translations API; you can use the official OpenAI Python client to interact with it. Whisper models can translate audio from one of the 55 non-English supported languages into English. Please mind that the popular openai/whisper-large-v3-turbo model does not support translating.

Note

To use the Translation API, please install with extra audio dependencies using pip install vllm[audio].

Code example:  examples/online_serving/openai_translation_client.py

Extra Parameters¶
The following sampling parameters are supported.


    use_beam_search: bool = False
    """Whether or not beam search should be used."""

    n: int = 1
    """The number of beams to be used in beam search."""

    length_penalty: float = 1.0
    """Length penalty to be used for beam search."""

    include_stop_str_in_output: bool = False
    """Whether to include the stop strings in output text."""

    seed: int | None = Field(None, ge=_LONG_INFO.min, le=_LONG_INFO.max)
    """The seed to use for sampling."""

    temperature: float = Field(default=0.0)
    """The sampling temperature, between 0 and 1.

    Higher values like 0.8 will make the output more random, while lower values
    like 0.2 will make it more focused / deterministic. If set to 0, the model
    will use [log probability](https://en.wikipedia.org/wiki/Log_probability)
    to automatically increase the temperature until certain thresholds are hit.
    """
The following extra parameters are supported:


    language: str | None = None
    """The language of the input audio we translate from.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format
    will improve accuracy.
    """

    to_language: str | None = None
    """The language of the input audio we translate to.

    Please note that this is not supported by all models, refer to the specific
    model documentation for more details.
    For instance, Whisper only supports `to_language=en`.
    """

    stream: bool | None = False
    """Custom field not present in the original OpenAI definition. When set,
    it will enable output to be streamed in a similar fashion as the Chat
    Completion endpoint.
    """
    # Flattened stream option to simplify form data.
    stream_include_usage: bool | None = False
    stream_continuous_usage_stats: bool | None = False

    max_completion_tokens: int | None = None
    """The maximum number of tokens to generate."""
Realtime API¶
The Realtime API provides WebSocket-based streaming audio transcription, allowing real-time speech-to-text as audio is being recorded.

Note

To use the Realtime API, please install with extra audio dependencies using uv pip install vllm[audio].

Audio Format¶
Audio must be sent as base64-encoded PCM16 audio at 16kHz sample rate, mono channel.

Protocol Overview¶
Client connects to ws://host/v1/realtime
Server sends session.created event
Client optionally sends session.update with model/params
Client sends input_audio_buffer.commit when ready
Client sends input_audio_buffer.append events with base64 PCM16 chunks
Server sends transcription.delta events with incremental text
Server sends transcription.done with final text + usage
Repeat from step 5 for next utterance
Optionally, client sends input_audio_buffer.commit with final=True to signal audio input is finished. Useful when streaming audio files
Client → Server Events¶
Event	Description
input_audio_buffer.append	Send base64-encoded audio chunk: {"type": "input_audio_buffer.append", "audio": "<base64>"}
input_audio_buffer.commit	Trigger transcription processing or end: {"type": "input_audio_buffer.commit", "final": bool}
session.update	Configure session: {"type": "session.update", "model": "model-name"}
Server → Client Events¶
Event	Description
session.created	Connection established with session ID and timestamp
transcription.delta	Incremental transcription text: {"type": "transcription.delta", "delta": "text"}
transcription.done	Final transcription with usage stats
error	Error notification with message and optional code
Example Clients¶
openai_realtime_client.py - Upload and transcribe an audio file
openai_realtime_microphone_client.py - Gradio demo for live microphone transcription
Tokenizer API¶
Our Tokenizer API is a simple wrapper over HuggingFace-style tokenizers. It consists of two endpoints:

/tokenize corresponds to calling tokenizer.encode().
/detokenize corresponds to calling tokenizer.decode().
Score API¶
Score Template¶
Some scoring models require a specific prompt format to work correctly. You can specify a custom score template using the --chat-template parameter (see Chat Template).

Score templates are supported for cross-encoder models only. If you are using an embedding model for scoring, vLLM does not apply a score template.

Like chat templates, the score template receives a messages list. For scoring, each message has a role attribute—either "query" or "document". For the usual kind of point-wise cross-encoder, you can expect exactly two messages: one query and one document. To access the query and document content, use Jinja's selectattr filter:

Query: {{ (messages | selectattr("role", "eq", "query") | first).content }}
Document: {{ (messages | selectattr("role", "eq", "document") | first).content }}
This approach is more robust than index-based access (messages[0], messages[1]) because it selects messages by their semantic role. It also avoids assumptions about message ordering if additional message types are added to messages in the future.

Example template file:  examples/pooling/score/template/nemotron-rerank.jinja

Ray Serve LLM¶
Ray Serve LLM enables scalable, production-grade serving of the vLLM engine. It integrates tightly with vLLM and extends it with features such as auto-scaling, load balancing, and back-pressure.

Key capabilities:

Exposes an OpenAI-compatible HTTP API as well as a Pythonic API.
Scales from a single GPU to a multi-node cluster without code changes.
Provides observability and autoscaling policies through Ray dashboards and metrics.
The following example shows how to deploy a large model like DeepSeek R1 with Ray Serve LLM:  examples/online_serving/ray_serve_deepseek.py.

Learn more about Ray Serve LLM with the official Ray Serve LLM documentation.