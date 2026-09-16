#!/bin/sh
set -eu

mc alias set lasuite http://minio:9000 lasuite password

mc mb --ignore-existing lasuite/impress-media-storage
mc version enable lasuite/impress-media-storage || true
mc mb --ignore-existing lasuite/meet-media-storage
mc mb --ignore-existing lasuite/dictaphone-media-storage
mc mb --ignore-existing lasuite/dictaphone-media-alpha
mc mb --ignore-existing lasuite/dictaphone-media-beta

mc admin user add lasuite impress password || true
mc admin user add lasuite meet password || true
mc admin user add lasuite dictaphone-default password-default || true
mc admin user add lasuite dictaphone-alpha password-alpha || true
mc admin user add lasuite dictaphone-beta password-beta || true

printf '%s' '{"Version":"2012-10-17","Statement":[{"Action":["s3:*"],"Effect":"Allow","Resource":["arn:aws:s3:::impress-media-storage","arn:aws:s3:::impress-media-storage/*"]}]}' >/tmp/impress-policy.json
printf '%s' '{"Version":"2012-10-17","Statement":[{"Action":["s3:*"],"Effect":"Allow","Resource":["arn:aws:s3:::meet-media-storage","arn:aws:s3:::meet-media-storage/*"]}]}' >/tmp/meet-policy.json
printf '%s' '{"Version":"2012-10-17","Statement":[{"Action":["s3:*"],"Effect":"Allow","Resource":["arn:aws:s3:::dictaphone-media-storage","arn:aws:s3:::dictaphone-media-storage/*"]}]}' >/tmp/dictaphone-default-policy.json
printf '%s' '{"Version":"2012-10-17","Statement":[{"Action":["s3:*"],"Effect":"Allow","Resource":["arn:aws:s3:::dictaphone-media-alpha","arn:aws:s3:::dictaphone-media-alpha/*"]}]}' >/tmp/dictaphone-alpha-policy.json
printf '%s' '{"Version":"2012-10-17","Statement":[{"Action":["s3:*"],"Effect":"Allow","Resource":["arn:aws:s3:::dictaphone-media-beta","arn:aws:s3:::dictaphone-media-beta/*"]}]}' >/tmp/dictaphone-beta-policy.json

mc admin policy create lasuite impress-bucket-policy /tmp/impress-policy.json || true
mc admin policy create lasuite meet-bucket-policy /tmp/meet-policy.json || true
mc admin policy create lasuite dictaphone-default-bucket-policy /tmp/dictaphone-default-policy.json || true
mc admin policy create lasuite dictaphone-alpha-bucket-policy /tmp/dictaphone-alpha-policy.json || true
mc admin policy create lasuite dictaphone-beta-bucket-policy /tmp/dictaphone-beta-policy.json || true

mc admin policy attach lasuite impress-bucket-policy --user impress || true
mc admin policy attach lasuite meet-bucket-policy --user meet || true
mc admin policy attach lasuite dictaphone-default-bucket-policy --user dictaphone-default || true
mc admin policy attach lasuite dictaphone-alpha-bucket-policy --user dictaphone-alpha || true
mc admin policy attach lasuite dictaphone-beta-bucket-policy --user dictaphone-beta || true
