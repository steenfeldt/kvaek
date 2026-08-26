from ninja import NinjaAPI

from accounts.api import router as accounts_router
from billing.api import router as billing_router
from campaigns.api import router as campaigns_router
from discovery.api import router as discovery_router
from messaging.api import router as messaging_router

api = NinjaAPI(title="Marketplace API")


@api.get("/health", auth=None)
def health(request):
    return {"status": "ok"}


api.add_router("", accounts_router)
api.add_router("", discovery_router)
api.add_router("", campaigns_router)
api.add_router("", billing_router)
api.add_router("", messaging_router)
