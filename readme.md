## How to deploy FarBox on your owner VPS?

### Initialize environment
Ubuntu 18.04 is the recommended operating system, other Linux operating systems, the basic logic is same.

Setup basic environment and install Docker first.
```bash
sudo apt-get update && sudo apt-get install -y python-pip  && sudo apt-get install -y docker.io
```

Note: the installation steps of Docker may also change dynamically, you can refer to the official Docker installation documentation for details.


### Deploy FarBox (FarBox Bucket)

```bash
sudo docker pull hepochen/farbox_bucket:latest                                         
sudo pip install xserver
sudo xserver_package deploy farbox memcache=200mb && sudo xserver start farbox
```

Execute the following command to automatically start the FarBox service when the server is restarted:
```bash
sudo xserver install_start
```


Alternatively, you can run the following command to check every 2 minutes if the FarBox service container has failed and needs to be restarted:
```bash
sudo xserver install_live
```

At this point, FarBox is already running, visit `http://your-ip` for the first installation on the web side; of course that ports 80 and 443 of the service should be open.

After initializing the first Bucket on the web side, you may need to restart the service (if the data on the web side is normal, you don't need to deal with it): 
```bash
docker exec -it farbox bash
supervisorctl restart all
```

### Where the data stored?
- /data/farbox_ssdb: core database 
- /data/farbox_es: Elasticsearch indexes
- /data/farbox: core web server data
- /data/log/farbox: log files
- /home/run/farbox: env configs for FarBox

Note: if you want to re-install Farbox, maybe you should try to remove `/data/farbox_ssdb` first, it depends.


-----------


## Clients
On iPhone and iPad, you can try **Metion**, for macOS, you can try [MarkEditor](https://markeditor.com) and [Markdown.app](https://markdown.app).

Of course Python script can sync with FarBox too, the contents of script are similar to the blow:
```python
from farbox_bucket.client.sync import sync_to_farbox, sync_from_farbox

sync_to_farbox(
    node = "<your_web_server_node>",
    root = "<your_local_folder_path>",
    private_key = "<private_key_for_bucket>"
)

```
