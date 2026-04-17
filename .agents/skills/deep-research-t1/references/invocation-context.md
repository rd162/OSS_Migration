# MCP Invocation Context — deep-research-t1

Setup and activation details for MCP-compatible editors.
Loaded on demand from the main SKILL.md.

---

## MCP environments (Zed, Cursor, Windsurf, Claude Desktop, etc.)

In environments without native skill support, this skill is delivered via an
MCP bridge such as **SkillPort** (`skillport-mcp`) or **Skillz**.
There is no `/deep-research` slash command and no `$ARGUMENTS`.

**How it works:**

- **SkillPort** (recommended): exposes `search_skills` + `load_skill` tools.
  The agent searches for "deep research" → loads this skill on demand.
  Progressive disclosure: metadata only until `load_skill` is called.
- **Skillz**: exposes each skill as one MCP Tool named after the skill.
  Simpler but loads all skill tools into every prompt (context bloat at scale).

**Zed setup (SkillPort):**

```json
{
  "context_servers": {
    "skillport": {
      "source": "custom",
      "command": "uvx",
      "args": ["skillport-mcp"],
      "env": {
        "SKILLPORT_SKILLS_DIR": "/path/to/your/skills"
      }
    }
  }
}
```

**Zed setup (Skillz, simpler):**

```json
{
  "context_servers": {
    "skillz": {
      "source": "custom",
      "command": "uvx",
      "args": ["skillz@latest", "/path/to/your/skills"]
    }
  }
}
```

**In MCP mode, topic and output mode are inferred from the conversation.**
The agent reads the full skill body and applies the Disambiguation Step,
Δ1-Δ7 protocol, and File Output section based on what the user asked for —
no argument parsing required. `$ARGUMENTS` blocks are simply skipped.
