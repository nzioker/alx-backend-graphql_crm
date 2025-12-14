import graphene
from crm.schema import Query as CRMQuery  # Import from crm schema

class Query(CRMQuery, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
