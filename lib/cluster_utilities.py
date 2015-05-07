import etc.cluster_config as cl_conf

def remote_to_local_filename(remote_filename, local_media_parent=None):
    if local_media_parent is None:
        local_media_parent = cl_conf.LOCAL_CACHE_DIR
    return os.path.join(
        local_media_parent,
        remote_filename[remote_filename.find('media'):]
    )