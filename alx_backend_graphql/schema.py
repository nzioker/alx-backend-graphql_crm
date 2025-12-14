import graphene  # Import graphene

class Query(graphene.ObjectType):  # Class Query exists and inherits graphene.ObjectType
    hello = graphene.String()
    
    def resolve_hello(self, info):
        return "Hello, GraphQL!"

schema = graphene.Schema(query=Query)  # Schema with Query class
