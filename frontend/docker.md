# AISHA Frontend — Docker Commands

## Build the image
```
cd frontend
docker build -t aisha-frontend .
```

## Run it (foreground)
```
docker run -p 3000:80 aisha-frontend
```
App available at: http://localhost:3000

## Run it (background/detached)
```
docker run -d -p 3000:80 --name aisha-frontend-container aisha-frontend
```

## Check it's running
```
docker ps
```

## View logs
```
docker logs -f aisha-frontend-container
```

## Stop it
```
docker stop aisha-frontend-container
```

## Remove the container
```
docker rm aisha-frontend-container
```

## Rebuild after code changes
```
docker build -t aisha-frontend .
docker stop aisha-frontend-container
docker rm aisha-frontend-container
docker run -d -p 3000:80 --name aisha-frontend-container aisha-frontend
```

## Run full stack (once backend Dockerfile exists)
```
cd ..
docker compose build
docker compose up
```
Add `-d` to run detached. Stop with:
```
docker compose down
```
