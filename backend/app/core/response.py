def success_response(data=None, pagination=None, msg="success", code=0):
    result = dict(code=code, data=data, message=msg)
    if pagination is not None:
        result.update(pagination=pagination)
    return result


def fail_response(data=None, code=1, msg="fail"):
    return dict(code=code, data=data, message=msg)