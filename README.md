** 1) Démarrer Meet (service de transcription) **

```
cd ~/lasuite/meet
docker compose -f compose.yml -f compose.albert.yml up -d \
  redis-summary minio createbuckets app-summary-dev \
  celery-summary-transcribe celery-summary-summarize celery-summary-webhook
docker compose -f compose.yml -f compose.albert.yml ps
```

** 2) Démarrer Dictaphone (éviter le conflit DB/hostname) ** 
```
cd ~/lasuite/dictaphone

# base services d'abord
docker compose up -d postgresql redis kc_postgresql keycloak

# migrations ensuite (sans dépendances auto)
docker compose run --rm --no-deps app-dev python manage.py migrate

# app + workers + nginx + front
docker compose up -d --no-deps \
  app-dev celery-dev celery-audio-dev nginx frontend
docker compose exec app-dev getent hosts postgresql
docker compose exec app-dev python manage.py check
docker compose ps
```
** 3) URL & login ** 
```
Dictaphone: http://localhost:3000
Login: dictaphone / dictaphone
```
** 4) Arrêt propre (sans perdre les volumes) **
```
cd ~/lasuite/dictaphone && docker compose stop
cd ~/lasuite/meet && docker compose -f compose.yml -f compose.albert.yml stop
```
 ** MINIO URL & login **
```
ObjectStore: http://localhost:9001
Login: meet / password
```
