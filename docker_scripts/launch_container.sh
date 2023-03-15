docker run \
 -d \
 --shm-size=4g \
 --memory=15g \
 --user 1000:1000 \
 --name erlygin_face_eval_new \
 --rm -it \
 --init \
 -v /home/leonid/projects/antiYoyProject:/app \
 --gpus all \
 antiyoy bash