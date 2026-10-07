from slowapi import Limiter

from api.services.network.get_ip import get_real_ip

limiter = Limiter(key_func=get_real_ip)