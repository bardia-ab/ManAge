from dataclasses import dataclass, field
from typing import List

@dataclass
class CUT_Delay:
    origin          :   str     = 'X-1Y-1'
    CUT_idx         :   int     = -1
    TC_idx          :   int     = -1
    seg_idx         :   int     = -1
    path_idx        :   int     = -1        # this is the index of the CUT in the segment
    rising_delay    :   float   = 0
    falling_delay   :   float   = 0
    edges           :   [tuple] = field(default_factory=list)

    def __eq__(self, other):
        return type(self) == type(other) and self.origin == other.origin and self.CUT_idx == other.CUT_idx and self.TC_idx == other.TC_idx

    def __hash__(self):
        return hash((self.origin, self.CUT_idx, self.TC_idx))

@dataclass
class CUTs_List:
    CUTs    :   List[CUT_Delay]

    def filter_CUTs(self, **attributes):
        all_cuts = self.CUTs.copy()
        for k, v in attributes.items():
            cuts = set()
            for cut in all_cuts:
                if getattr(cut, k) == v:
                    cuts.add(cut)

            all_cuts = cuts.copy()

        return all_cuts