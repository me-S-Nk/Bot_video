import instaloader
L = instaloader.Instaloader(download_videos=False, save_metadata=False, download_comments=False)
try:
    post = instaloader.Post.from_shortcode(L.context, "DXCcXeuiGXj")
    for i, node in enumerate(post.get_sidecar_nodes()):
        print(f"Node {i}: {node.is_video}")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
