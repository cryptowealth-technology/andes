"""
Synchronous generator classes
"""

import logging
from andes.core.model import Model, ModelData, ModelConfig  # NOQA
from andes.core.param import DataParam, NumParam, ExtParam  # NOQA
from andes.core.var import Algeb, State, ExtAlgeb  # NOQA
from andes.core.limiter import Comparer, SortedLimiter  # NOQA
from andes.core.service import Service, ExtService  # NOQA
logger = logging.getLogger(__name__)


class GEN2AxisData(ModelData):
    def __init__(self):
        super().__init__()

        self.Sn = NumParam(default=100.0, info="Power rating")
        self.Vn = NumParam(default=110.0, info="AC voltage rating")
        self.fn = NumParam(default=60.0, info="rated frequency")

        self.bus = DataParam(info="interface bus idx", mandatory=True)
        self.gen = DataParam(info="static generator index", mandatory=True)
        self.coi = DataParam(info="center of inertia index")

        self.D = NumParam(default=0.0, info="Damping coefficient", power=True)
        self.M = NumParam(default=6, info="machine start up time (2xH)", non_zero=True, power=True)
        self.ra = NumParam(default=0.0, info="armature resistance", z=True)
        self.xd1 = NumParam(default=1.9, info="synchronous reactance", z=True)
        self.xq1 = NumParam(default=0.5, info="q-axis transient reactance", mandatory=True, z=True)
        self.xl = NumParam(default=0.0, info="leakage reactance", z=True)
        self.xd = NumParam(default=1.9, info="d-axis synchronous reactance", mandatory=True, z=True)
        self.xq = NumParam(default=1.7, info="q-axis synchronous reactance", z=True)
        self.Td10 = NumParam(default=8.0, info="d-axis transient time constant", mandatory=True)
        self.Tq10 = NumParam(default=0.8, info="q-axis transient time constant", mandatory=True)

        self.gammap = NumParam(default=1.0, info="active power ratio of all generators on this bus")
        self.gammaq = NumParam(default=1.0, info="reactive power ratio")
        self.kp = NumParam(default=0., info="active power feedback gain")
        self.kw = NumParam(default=0., info="speed feedback gain")

        self.S10 = NumParam(default=0., info="first saturation factor")
        self.S12 = NumParam(default=0., info="second saturation factor")


class GEN2Axis(GEN2AxisData, Model):
    def __init__(self, system=None, name=None, config=None):
        GEN2AxisData.__init__(self)
        Model.__init__(self, name, system, config)

        self.flags.update({'tds': True})

        self.a = ExtAlgeb(model='Bus', src='a', indexer=self.bus)
        self.v = ExtAlgeb(model='Bus', src='v', indexer=self.bus)

        self.delta = State(v_init='u * im(log(E / abs(E)))')
        self.omega = State(v_init='1')
        self.e1d = State(v_init='vq + ra * Iq + xd1 * Id')
        self.e1q = State(v_init='vd + ra * Id - xq1 * Iq')
        self.vd = Algeb(v_init='re(vdq)')
        self.vq = Algeb(v_init='im(vdq)')
        self.tm = Algeb(v_init='tm0')
        self.vf = Algeb(v_init='vf0')

        # NOTE: assume that one static gen can only correspond to one syn
        # Does not support automatic PV gen combination
        self.p0 = ExtService(model='PV', src='p', indexer=self.gen)
        self.q0 = ExtService(model='PV', src='q', indexer=self.gen)

        self.Vc = Service(v_str='v * exp(1j * a)')
        self.S = Service(v_str='p0 - 1j * q0')
        self.Ic = Service(v_str='S / conj(Vc)')
        self.E = Service(v_str='Vc + Ic * (ra + 1j * xq)')

        self.vdq = Service(v_str='u * (Vc * exp(1j * 0.5 * pi - delta))')
        self.Idq = Service(v_str='u * (Ic * exp(1j * 0.5 * pi - delta))')
        self.Id = Service(v_str='re(Idq)')
        self.Iq = Service(v_str='im(Idq)')
        self.tm0 = Service(v_str='(vq + ra * Iq) * Iq + (vd + ra * Id) * Id')
        self.vf0 = Service(v_numeric=self._vf0)

        # DAE

        # TODO: substitute static generators

    @staticmethod
    def _vf0(e1q, xd, xd1, Id, **kwargs):
        return e1q + (xd - xd1) * Id
