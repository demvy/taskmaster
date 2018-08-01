import os
import signal


_signames = None


def get_signame(sig):
    """
    Return a symbolic name for a signal from signal module
    """
    if _signames is None:
        _init_signames()
    return _signames.get(sig) or "signal %d" % sig


def _init_signames():
    global _signames
    d = {}
    for k, v in signal.__dict__.items():
        k_startswith = getattr(k, "startswith", None)
        if k_startswith is None:
            continue
        if k_startswith("SIG") and not k_startswith("SIG_"):
            d[v] = k
    _signames = d


def decode_wait_status(status):
    """Decode the status returned by wait() or waitpid().
    Return a tuple (exitstatus, message) where exitstatus is the exit
    status, or -1 if the process was killed by a signal; and message
    is telling what happened.
    """
    if os.WIFEXITED(status):
        es = os.WEXITSTATUS(status) & 0xffff
        msg = "exit status %s" % es
        return es, msg
    elif os.WIFSIGNALED(status):
        sig = os.WTERMSIG(status)
        msg = "terminated by %s" % get_signame(sig)
        if hasattr(os, "WCOREDUMP"):
            iscore = os.WCOREDUMP(status)
        else:
            iscore = status & 0x80
        if iscore:
            msg += " (core dumped)"
        return -1, msg
    else:
        msg = "unknown termination cause 0x%04x" % status
        return -1, msg