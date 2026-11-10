import time
import pytest

def test_protocol_message_serialization_throughput():
    from tunnel.protocol import Message, MessageType
    
    start = time.perf_counter()
    iterations = 5000
    for i in range(iterations):
        msg = Message(type=MessageType.PING, payload={"seq": i})
        serialized = msg.to_json()
        assert len(serialized) > 0
    duration = time.perf_counter() - start
    
    # 5,000 serializations should take less than 0.5s
    assert duration < 0.5, f"Serialization too slow: {duration:.4f}s for {iterations} messages"
