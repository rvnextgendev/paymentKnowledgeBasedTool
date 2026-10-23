var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.MapPost("/payments", (PaymentRequest request) =>
{
    if (request.Amount < 0) return Results.BadRequest("Amount must be greater than zero");
    if (request.Currency != "USD") return Results.BadRequest("Only USD supported in demo");
    return Results.Ok(new { Status = "Accepted", request.Amount });
});
app.Run();
record PaymentRequest(decimal Amount, string Currency);
