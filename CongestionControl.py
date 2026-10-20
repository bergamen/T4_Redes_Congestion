SLOW_START = 0
CONGESTION_AVOIDANCE = 1
class CongestionControl:
    def __init__(self,MSS:int):
        self.current_state = SLOW_START
        self.MSS = MSS
        self.cwmd = MSS
        self.ssthresh = None

    def get_cwnd(self) -> bytes:
        return self.cwmd

    def get_MSS_in_cwnd(self) -> int:
        return int(self.cwmd / self.MSS)

    def event_ack_received(self):
        if self.current_state == SLOW_START:
            self.cwmd += self.MSS
            if self.ssthresh != None and self.cwmd >= self.ssthresh:
                self.current_state = CONGESTION_AVOIDANCE
        elif self.current_state == CONGESTION_AVOIDANCE:
            self.cwmd += (self.MSS/self.get_MSS_in_cwnd())

    def event_timeout(self):
        if self.ssthresh == None or self.current_state == CONGESTION_AVOIDANCE:
            self.ssthresh = int(self.cwmd / 2)
            self.cwmd = self.MSS
        if self.current_state == CONGESTION_AVOIDANCE:
            self.current_state = SLOW_START 


    def is_state_slow_start(self) -> bool:
        return self.current_state == SLOW_START

    def is_state_congestion_avoidance(self) -> bool:
            return self.current_state == CONGESTION_AVOIDANCE

    def get_ssthresh(self):
        return self.ssthresh