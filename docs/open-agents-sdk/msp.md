Model context protocol (MCP)
The Model context protocol (MCP) standardises how applications expose tools and context to language models. From the official documentation:

MCP is an open protocol that standardizes how applications provide context to LLMs. Think of MCP like a USB-C port for AI applications. Just as USB-C provides a standardized way to connect your devices to various peripherals and accessories, MCP provides a standardized way to connect AI models to different data sources and tools.

The Agents Python SDK understands multiple MCP transports. This lets you reuse existing MCP servers or build your own to expose filesystem, HTTP, or connector backed tools to an agent.

Choosing an MCP integration
Before wiring an MCP server into an agent decide where the tool calls should execute and which transports you can reach. The matrix below summarises the options that the Python SDK supports.

What you need	Recommended option
Let OpenAI's Responses API call a publicly reachable MCP server on the model's behalf	Hosted MCP server tools via HostedMCPTool
Connect to Streamable HTTP servers that you run locally or remotely	Streamable HTTP MCP servers via MCPServerStreamableHttp
Talk to servers that implement HTTP with Server-Sent Events	HTTP with SSE MCP servers via MCPServerSse
Launch a local process and communicate over stdin/stdout	stdio MCP servers via MCPServerStdio
The sections below walk through each option, how to configure it, and when to prefer one transport over another.

Agent-level MCP configuration
In addition to choosing a transport, you can tune how MCP tools are prepared by setting Agent.mcp_config.


from agents import Agent

agent = Agent(
    name="Assistant",
    mcp_servers=[server],
    mcp_config={
        # Try to convert MCP tool schemas to strict JSON schema.
        "convert_schemas_to_strict": True,
        # If None, MCP tool failures are raised as exceptions instead of
        # returning model-visible error text.
        "failure_error_function": None,
    },
)
Notes:

convert_schemas_to_strict is best-effort. If a schema cannot be converted, the original schema is used.
failure_error_function controls how MCP tool call failures are surfaced to the model.
When failure_error_function is unset, the SDK uses the default tool error formatter.
Server-level failure_error_function overrides Agent.mcp_config["failure_error_function"] for that server.
Shared patterns across transports
After you choose a transport, most integrations need the same follow-up decisions:

How to expose only a subset of tools (Tool filtering).
Whether the server also provides reusable prompts (Prompts).
Whether list_tools() should be cached (Caching).
How MCP activity appears in traces (Tracing).
For local MCP servers (MCPServerStdio, MCPServerSse, MCPServerStreamableHttp), approval policies and per-call _meta payloads are also shared concepts. The Streamable HTTP section shows the most complete examples, and the same patterns apply to the other local transports.

1. Hosted MCP server tools
Hosted tools push the entire tool round-trip into OpenAI's infrastructure. Instead of your code listing and calling tools, the HostedMCPTool forwards a server label (and optional connector metadata) to the Responses API. The model lists the remote server's tools and invokes them without an extra callback to your Python process. Hosted tools currently work with OpenAI models that support the Responses API's hosted MCP integration.

Basic hosted MCP tool
Create a hosted tool by adding a HostedMCPTool to the agent's tools list. The tool_config dict mirrors the JSON you would send to the REST API:


import asyncio

from agents import Agent, HostedMCPTool, Runner

async def main() -> None:
    agent = Agent(
        name="Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "gitmcp",
                    "server_url": "https://gitmcp.io/openai/codex",
                    "require_approval": "never",
                }
            )
        ],
    )

    result = await Runner.run(agent, "Which language is this repository written in?")
    print(result.final_output)

asyncio.run(main())
The hosted server exposes its tools automatically; you do not add it to mcp_servers.

If you want hosted tool search to load a hosted MCP server lazily, set tool_config["defer_loading"] = True and add ToolSearchTool to the agent. This is supported only on OpenAI Responses models. See Tools for the complete tool-search setup and constraints.

Streaming hosted MCP results
Hosted tools support streaming results in exactly the same way as function tools. Use Runner.run_streamed to consume incremental MCP output while the model is still working:


result = Runner.run_streamed(agent, "Summarise this repository's top languages")
async for event in result.stream_events():
    if event.type == "run_item_stream_event":
        print(f"Received: {event.item}")
print(result.final_output)
Optional approval flows
If a server can perform sensitive operations you can require human or programmatic approval before each tool execution. Configure require_approval in the tool_config with either a single policy ("always", "never") or a dict mapping tool names to policies. To make the decision inside Python, provide an on_approval_request callback.


from agents import MCPToolApprovalFunctionResult, MCPToolApprovalRequest

SAFE_TOOLS = {"read_project_metadata"}

def approve_tool(request: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    if request.data.name in SAFE_TOOLS:
        return {"approve": True}
    return {"approve": False, "reason": "Escalate to a human reviewer"}

agent = Agent(
    name="Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gitmcp",
                "server_url": "https://gitmcp.io/openai/codex",
                "require_approval": "always",
            },
            on_approval_request=approve_tool,
        )
    ],
)
The callback can be synchronous or asynchronous and is invoked whenever the model needs approval data to keep running.

Connector-backed hosted servers
Hosted MCP also supports OpenAI connectors. Instead of specifying a server_url, supply a connector_id and an access token. The Responses API handles authentication and the hosted server exposes the connector's tools.


import os

HostedMCPTool(
    tool_config={
        "type": "mcp",
        "server_label": "google_calendar",
        "connector_id": "connector_googlecalendar",
        "authorization": os.environ["GOOGLE_CALENDAR_AUTHORIZATION"],
        "require_approval": "never",
    }
)
Fully working hosted tool samples—including streaming, approvals, and connectors—live in examples/hosted_mcp.

2. Streamable HTTP MCP servers
When you want to manage the network connection yourself, use MCPServerStreamableHttp. Streamable HTTP servers are ideal when you control the transport or want to run the server inside your own infrastructure while keeping latency low.


import asyncio
import os

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings

async def main() -> None:
    token = os.environ["MCP_SERVER_TOKEN"]
    async with MCPServerStreamableHttp(
        name="Streamable HTTP Python Server",
        params={
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": f"Bearer {token}"},
            "timeout": 10,
        },
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use the MCP tools to answer the questions.",
            mcp_servers=[server],
            model_settings=ModelSettings(tool_choice="required"),
        )

        result = await Runner.run(agent, "Add 7 and 22.")
        print(result.final_output)

asyncio.run(main())
The constructor accepts additional options:

client_session_timeout_seconds controls HTTP read timeouts.
use_structured_content toggles whether tool_result.structured_content is preferred over textual output.
max_retry_attempts and retry_backoff_seconds_base add automatic retries for list_tools() and call_tool().
tool_filter lets you expose only a subset of tools (see Tool filtering).
require_approval enables human-in-the-loop approval policies on local MCP tools.
failure_error_function customizes model-visible MCP tool failure messages; set it to None to raise errors instead.
tool_meta_resolver injects per-call MCP _meta payloads before call_tool().
Approval policies for local MCP servers
MCPServerStdio, MCPServerSse, and MCPServerStreamableHttp all accept require_approval.

Supported forms:

"always" or "never" for all tools.
True / False (equivalent to always/never).
A per-tool map, for example {"delete_file": "always", "read_file": "never"}.
A grouped object: {"always": {"tool_names": [...]}, "never": {"tool_names": [...]}}.

async with MCPServerStreamableHttp(
    name="Filesystem MCP",
    params={"url": "http://localhost:8000/mcp"},
    require_approval={"always": {"tool_names": ["delete_file"]}},
) as server:
    ...
For a full pause/resume flow, see Human-in-the-loop and examples/mcp/get_all_mcp_tools_example/main.py.

Per-call metadata with tool_meta_resolver
Use tool_meta_resolver when your MCP server expects request metadata in _meta (for example, tenant IDs or trace context). The example below assumes you pass a dict as context to Runner.run(...).


from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext


def resolve_meta(context: MCPToolMetaContext) -> dict[str, str] | None:
    run_context_data = context.run_context.context or {}
    tenant_id = run_context_data.get("tenant_id")
    if tenant_id is None:
        return None
    return {"tenant_id": str(tenant_id), "source": "agents-sdk"}


server = MCPServerStreamableHttp(
    name="Metadata-aware MCP",
    params={"url": "http://localhost:8000/mcp"},
    tool_meta_resolver=resolve_meta,
)
If your run context is a Pydantic model, dataclass, or custom class, read the tenant ID with attribute access instead.

MCP tool outputs: text and images
When an MCP tool returns image content, the SDK maps it to image tool output entries automatically. Mixed text/image responses are forwarded as a list of output items, so agents can consume MCP image results the same way they consume image output from regular function tools.

3. HTTP with SSE MCP servers
Warning

The MCP project has deprecated the Server-Sent Events transport. Prefer Streamable HTTP or stdio for new integrations and keep SSE only for legacy servers.

If the MCP server implements the HTTP with SSE transport, instantiate MCPServerSse. Apart from the transport, the API is identical to the Streamable HTTP server.


from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.mcp import MCPServerSse

workspace_id = "demo-workspace"

async with MCPServerSse(
    name="SSE Python Server",
    params={
        "url": "http://localhost:8000/sse",
        "headers": {"X-Workspace": workspace_id},
    },
    cache_tools_list=True,
) as server:
    agent = Agent(
        name="Assistant",
        mcp_servers=[server],
        model_settings=ModelSettings(tool_choice="required"),
    )
    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(result.final_output)
4. stdio MCP servers
For MCP servers that run as local subprocesses, use MCPServerStdio. The SDK spawns the process, keeps the pipes open, and closes them automatically when the context manager exits. This option is helpful for quick proofs of concept or when the server only exposes a command line entry point.


from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

current_dir = Path(__file__).parent
samples_dir = current_dir / "sample_files"

async with MCPServerStdio(
    name="Filesystem Server via npx",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(samples_dir)],
    },
) as server:
    agent = Agent(
        name="Assistant",
        instructions="Use the files in the sample directory to answer questions.",
        mcp_servers=[server],
    )
    result = await Runner.run(agent, "List the files available to you.")
    print(result.final_output)
5. MCP server manager
When you have multiple MCP servers, use MCPServerManager to connect them up front and expose the connected subset to your agents. See the MCPServerManager API reference for constructor options and reconnect behavior.


from agents import Agent, Runner
from agents.mcp import MCPServerManager, MCPServerStreamableHttp

servers = [
    MCPServerStreamableHttp(name="calendar", params={"url": "http://localhost:8000/mcp"}),
    MCPServerStreamableHttp(name="docs", params={"url": "http://localhost:8001/mcp"}),
]

async with MCPServerManager(servers) as manager:
    agent = Agent(
        name="Assistant",
        instructions="Use MCP tools when they help.",
        mcp_servers=manager.active_servers,
    )
    result = await Runner.run(agent, "Which MCP tools are available?")
    print(result.final_output)