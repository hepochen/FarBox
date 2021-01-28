# How to deploy FarBox on your owner Server/VPS

## Operating system Ubuntu 18.04
This is the recommended operating system, other Linux operating systems, the basic logic is the same, the specific explore yourself.


## Initialize server environment
step 1, basic environment
```bash
apt-get update
apt-get install -y python-pip
```

step 2, install Docker, as the installation steps of Docker may also change dynamically, you can refer to the official Docker installation documentation for details.
```bash
apt-get install -y docker.io
```


## Deploy FarBox (FarBox Bucket)

```bash
pip install xserver
docker pull hepochen/farbox_bucket:latest
xserver_package deploy farbox memcache=200mb && xserver start farbox
```

Execute the following command to automatically start the FarBox service when the server is restarted:
```bash
xserver install_start
```


Alternatively, you can run the following command to check every 2 minutes if the FarBox service container has failed and needs to be restarted:
```bash
xserver install_live
```

Note: xserver is a small software that I wrote separately to handle the logic related to server-side deployment.

At this point, FarBox is already running, visit `http://your-ip` for the first installation on the web side; of course that ports 80 and 443 of the service should be open.

Note: 
1. memcache is the basic cache service required for FarBox to run, if the server memory is limited, you can adjust the 200mb in the above demo to be smaller. 
2. You need to choose a template in the Dashboard first for your new bucket(site).


After initializing the first Bucket on the web side, you may need to restart the service (if the data on the web side is normal, you don't need to deal with it): ```bash
```bash
docker exec -it farbox bash
supervisorctl restart all
```



## Fresh install once again?
```bash
docker rm -f farbox
```

Then the following two directories should be removed using the command (not shown here additionally due to the potentially dangerous command associated with rm -rf)
```bash
/data/farbox_ssdb
/home/run/farbox
```

Then re-execute
```bash
docker pull hepochen/farbox_bucket:latest
xserver_package deploy farbox memcache=200mb
xserver start farbox
```
