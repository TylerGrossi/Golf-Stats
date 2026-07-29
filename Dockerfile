# Golf Analytics MCP server — Streamable HTTP, stateless, bearer-guarded.
#
# The whole dataset is under 1 MB and lives in git, so it is baked into the image
# rather than mounted: no volume, no database, nothing to attach at boot. The cost
# of that is a redeploy after each notebook run, which is a `git push`.
FROM python:3.14-slim

# Dependencies first so edits to golf_mcp.py do not re-resolve ~250 MB of wheels.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY paths.py golf_mcp.py ./
COPY data/ ./data/

# matplotlib writes a font cache on first use; without a writable HOME it warns and
# rebuilds that cache on every cold start, which shows up as a slow first chart.
ENV MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Nothing here needs root, and the app only ever reads its own files.
RUN useradd --create-home --uid 10001 golf && chown -R golf:golf /app
USER golf

# PORT is what makes golf_mcp.py choose Streamable HTTP over stdio; hosts that inject
# their own PORT override this. MCP_AUTH_TOKEN is deliberately absent — it is a secret,
# set it with `fly secrets set`, and the server refuses to start in HTTP mode without it.
ENV PORT=8080
EXPOSE 8080

# Pre-warm the font cache and fail the build if the module cannot import or a tool
# fails to register — cheaper to catch here than as a crash loop after deploy.
RUN python -c "import matplotlib.pyplot as plt; plt.figure()" && \
    python -c "import asyncio, golf_mcp; \
print('tools registered:', len(asyncio.run(golf_mcp.mcp.list_tools())))"

CMD ["python", "-X", "utf8", "golf_mcp.py"]
