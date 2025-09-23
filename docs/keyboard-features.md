# Qwen Code CLI Keyboard Features Guide

This document explains the enhanced keyboard features available in the Qwen Code CLI interactive mode.

## Instant Command Discovery

Press the forward slash (`/`) key at any time during an interactive session to instantly see a list of available commands without needing to press Enter.

### How it works:
1. While typing your message, press the `/` key
2. A list of available commands will immediately appear
3. You can continue typing your command or select one from the list
4. Press Enter to submit your command

### Example:
```
You: /  # Pressing '/' immediately shows:
Available Commands:
  /help    - Show available commands
  /clear   - Clear conversation history
  /stats   - Show conversation statistics
  exit     - Exit the session
  quit     - Exit the session
Tip: Press Tab for auto-completion
You: /
```

## Auto-completion

Use the Tab key to auto-complete commands when typing.

### How it works:
1. Start typing a command (e.g., `/he`)
2. Press the Tab key
3. The command will be auto-completed if there's a unique match (e.g., `/help`)
4. If multiple matches exist, the longest common prefix will be used
5. If no matches exist, the input remains unchanged

### Examples:
- Typing `/he` + Tab → completes to `/help`
- Typing `/c` + Tab → completes to `/clear`
- Typing `/h` + Tab → completes to `/help` (unique match)
- Typing `/` + Tab → remains as `/` (multiple matches with no common prefix extension)

## Supported Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/stats` | Show conversation statistics |
| `exit` | Exit the session |
| `quit` | Exit the session |

## Platform Support

These features work on both Windows and Unix-like systems (Linux, macOS):
- Windows: Uses `msvcrt` for keyboard input handling
- Unix/Linux/macOS: Uses `termios` and `tty` for raw keyboard input

## Fallback Behavior

If the enhanced keyboard features are not available on your system, the CLI will fall back to standard input methods without losing functionality.

## Tips for Best Experience

1. **Command Discovery**: Press `/` whenever you forget what commands are available
2. **Faster Typing**: Use Tab for auto-completion to reduce typing
3. **Error Prevention**: Auto-completion helps prevent typos in command names
4. **Efficiency**: Combine both features for the most efficient CLI experience