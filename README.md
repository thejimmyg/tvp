<!--
 * Copyright (c) James Gardner 2024 All Rights Reserved
 * This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
 * You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
 * 
 * This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
 * for more details.
 -->

rm -r tmp ; mkdir tmp; python3 zip.py .zipignore tmp/my_app.zip && cd tmp && python3 my_app.zip 127.0.0.1:9000 3 app:application && cd .. ;
micropython __main__.py 127.0.0.1:9000 1 app:application



pypy3 server.py 127.0.0.1:9000 8 app:application
wrk -t 8 -d 10 -c 128 'http://127.0.0.1:9000/hello?a=1&a=2&b=3'


python3 mimetypes_cli.py www > mimetypes.json
curl http://127.0.0.1/nav.css

python3 staticgz_cli.py www wwwgz wwwgz.json
curl -H 'accept-encoding: gzip' http://127.0.0.1:9000/nav.css -v > /dev/null


git tag v0.1.0
export ECR_REGISTRY=xxx.dkr.ecr.eu-west-2.amazonaws.com
export IMAGE_NAME=tvp
export TAG=`git describe --tags --exact-match`
export IMAGE="$ECR_REGISTRY/$IMAGE_NAME:$TAG"
test -z "$(git status --porcelain)" && docker buildx build --platform linux/amd64 -t $IMAGE . &&  docker run -p 9000:9000 $IMAGE || echo 'FAILED'

ifconfig | grep 'inet '
export NGROK_AUTHTOKEN=...
docker run --net=host -it -e NGROK_AUTHTOKEN=$NGROK_AUTHTOKEN ngrok/ngrok:latest http --domain=happily-fancy-eagle.ngrok-free.app 0.0.0.0:9000
