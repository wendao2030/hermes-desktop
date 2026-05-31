# Web Dashboard Discovery Notes

## Discovery Session
- **Date**: May 27, 2026
- **Context**: User asked about web interface for Hermes Agent

## Key Discoveries

### 1. Built-in Dashboard
- Hermes Agent has an **official built-in Web Dashboard**, not just community projects
- Accessed via `hermes dashboard` command
- Default port: 9119
- Uses FastAPI + React (Vite) stack

### 2. Dashboard Features
- Configuration management (config.yaml editor)
- API key management
- Session browsing and management
- Embedded TUI chat interface (via `--tui` flag)
- System monitoring

### 3. Command Options
```bash
# Basic usage
hermes dashboard                    # Start on port 9119
hermes dashboard --port 9120        # Custom port
hermes dashboard --no-open          # Don't auto-open browser
hermes dashboard --tui              # Enable embedded chat
hermes dashboard --skip-build       # Skip npm build
hermes dashboard --status           # Check running processes
hermes dashboard --stop             # Stop all dashboard processes
```

### 4. Security
- Default: binds to `127.0.0.1` only
- `--insecure` flag required for network binding
- Session tokens regenerated on each start
- CORS restricted to localhost origins

### 5. Technical Implementation
- **Backend**: FastAPI (`hermes_cli/web_server.py`)
- **Frontend**: React + Vite
- **Static files**: `hermes_cli/web_dist/`
- **Embedded TUI**: WebSocket PTY bridge to `hermes --tui`

### 6. Configuration
```yaml
# config.yaml
dashboard:
  theme: "default"  # Options: default, midnight, ember, mono, cyberpunk, rose
  port: 9119
  host: "127.0.0.1"
```

### 7. Access Patterns
- Direct browser: `http://localhost:9119`
- Embedded chat: `http://localhost:9119/chat` (when `--tui` enabled)
- API endpoints: `/api/*` (requires session token)

### 8. Development Notes
- Dashboard is part of main Hermes Agent repository
- Build process: `cd web && npm run build`
- Plugin system includes `example-dashboard` plugin
- S6 overlay service: `docker/s6-rc.d/dashboard`

## Verification Steps Used

1. **Command discovery**:
   ```bash
   hermes dashboard --help
   ```

2. **Process startup**:
   ```bash
   hermes dashboard --no-open --port 9120 &
   ```

3. **Port verification**:
   ```bash
   netstat -an | grep 9120
   ```

4. **HTTP access**:
   ```bash
   curl -s http://localhost:9120 | head -20
   ```

5. **Health check**:
   ```bash
   curl -s http://localhost:9120/api/health
   ```

## Common Issues & Solutions

### Dashboard won't start
- **Cause**: Port already in use
- **Solution**: Use different port with `--port`

### Build errors
- **Cause**: npm not installed or build fails
- **Solution**: Use `--skip-build` flag

### No browser opens
- **Cause**: Browser detection fails
- **Solution**: Use `--no-open` and manually open URL

### Authentication fails
- **Cause**: Session token mismatch
- **Solution**: Restart dashboard (tokens regenerate on start)

## Related Components
- `hermes_cli/web_server.py` - Main FastAPI server
- `hermes_cli/web_dist/` - Built frontend assets
- `plugins/example-dashboard/` - Example dashboard plugin
- `docker/s6-rc.d/dashboard` - Container service definition

## Useful for Future Sessions
- When users ask about web interfaces for Hermes
- When troubleshooting dashboard access
- When explaining Hermes features to new users
- When setting up visual monitoring of Hermes sessions