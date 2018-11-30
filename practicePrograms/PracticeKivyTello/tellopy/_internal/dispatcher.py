from . import event


class signal(object):
    All = event.Event("*")


signals = {}


def connect(receiver, connect_signal=signal.All):
    if connect_signal in signals:
        receivers = signals[connect_signal]
    else:
        receivers = signals[connect_signal] = []
    receivers.append(receiver)


def disconnect(receiver, disconnect_signal=signal.All):
    if disconnect_signal is signal.All:
        for disconnect_signal in signals:
            if receiver in signals[disconnect_signal]:
                signals[disconnect_signal].remove(receiver)
    elif disconnect_signal in signals:
        if receiver in signals[disconnect_signal]:
            signals[disconnect_signal].remove(receiver)


def send(send_signal, **named):
    if send_signal in signals:
        receivers = signals[send_signal] + signals[signal.All]
    else:
        receivers = signals[signal.All]
    for receiver in receivers:
        receiver(event=send_signal, **named)


if __name__ == '__main__':
    def handler_0(operate_drone, sender, **args):
        receives.append(0)
        print('Handler 0: Event = %s Sender = %s' % (str(operate_drone), str(sender)))
        print(args)

    def handler_1(operate_drone, sender, **args):
        receives.append(1)
        print('Handler 1: Event = %s Sender = %s' % (str(operate_drone), str(sender)))
        print(args)

    test_signal_0 = event.Event('Test signal 0')
    test_signal_1 = event.Event('Test signal 1')
    connect(handler_0, signal.All)
    connect(handler_1, test_signal_0)

    receives = []
    send(test_signal_0, sender=None)
    assert len(receives) == 2 and 0 in receives and 1 in receives

    receives = []
    send(test_signal_1, sender=None, data='Test data')
    assert len(receives) == 1 and 0 in receives

    disconnect(handler_1)

    receives = []
    send(test_signal_0, sender=None, arg0=0, arg1=1, arg2=2)
    assert len(receives) == 1 and 0 in receives
