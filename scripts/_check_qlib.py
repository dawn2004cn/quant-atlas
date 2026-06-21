try:
    import qlib

    print("qlib", qlib.__file__)
    for mod in (
        "qlib.contrib.data.dump_bin",
        "qlib.data.bin",
    ):
        try:
            __import__(mod)
            print("ok", mod)
        except Exception as e:
            print("fail", mod, e)
except Exception as e:
    print("NO_QLIB", e)
