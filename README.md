# colornode

Colorization microservice for [RootNode](https://github.com/stevwyman/rootnode).
It wraps [DDColor](https://github.com/piddnad/DDColor) behind FastAPI, the same
hub-and-spoke pattern as [facenode](https://github.com/stevwyman/facenode) and
[textnode](https://github.com/stevwyman/textnode).

The service is stateless: Rootnode sends image bytes, Colornode returns a
colorized JPEG, then forgets the photo. Weights are cached on a volume.

## Config

Rootless:

```yaml
services:
  colornode:
    image: localhost/colornode:latest
    container_name: colornode
    ports:
      - "8004:8000"
    restart: unless-stopped
    volumes:
      - models:/app/.ddcolor
    environment:
      DDCOLOR_MODEL: piddnad/ddcolor_paper_tiny

volumes:
  models:
    name: ddcolor_models
```

If the volume is created as root, fix ownership for the Red Hat user `1001`:

```sh
podman run --rm -u root -v ddcolor_models:/app/.ddcolor docker.io/library/alpine:latest chown -R 1001:0 /app/.ddcolor
```

Environment:

| Variable | Default | Meaning |
|---|---|---|
| `DDCOLOR_HOME` | `/app/.ddcolor` | Hugging Face cache / weight store |
| `DDCOLOR_MODEL` | `piddnad/ddcolor_paper_tiny` | Hub id or short name (`ddcolor_modelscope`, `ddcolor_artistic`, …) |
| `DDCOLOR_INPUT_SIZE` | `512` | Model input size |
| `DDCOLOR_JPEG_QUALITY` | `92` | Output JPEG quality |

`ddcolor_paper_tiny` is the lightest model. For better old-photo quality use
`piddnad/ddcolor_modelscope` (more RAM).

## Testing

```sh
curl -X POST -F "file=@old_photo.jpg" http://localhost:8004/colorize --output colorized.jpg
curl http://localhost:8004/health
```

Rootnode:

```env
COLORIZE_URL=http://colornode:8000
```
