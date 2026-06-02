import uvicorn


def dev() -> None:
    uvicorn.run("app.main:app", reload=True, host="0.0.0.0", port=8000)


def start() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    dev()
