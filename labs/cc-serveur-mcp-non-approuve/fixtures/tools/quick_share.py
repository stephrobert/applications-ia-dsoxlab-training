"""Stand-in for the quick-share MCP server added by a contribution.

The lab never starts it: the bench only reads its declaration in .mcp.json.
A real server of this kind would send files and the clipboard to a sharing
service outside the company.
"""

if __name__ == "__main__":
    raise SystemExit("simulated server: this lab never starts it")
