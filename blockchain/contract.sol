pragma solidity ^0.8.0;

contract ChargingSystem {
    // Mapeia endereços Ethereum para saldos
    mapping(address => uint256) public balances;
    // Mapeia endereços para IDs de veículos ou empresas
    mapping(address => string) public identities;
    // Histórico de transações
    struct Transaction {
        address from;
        address to;
        uint256 amount;
        string transactionType; // "reserva", "recarga", "pagamento"
        string data;
        uint256 timestamp;
    }
    Transaction[] public transactions;

    event TransactionRecorded(
        address indexed from,
        address indexed to,
        uint256 amount,
        string transactionType,
        string data,
        uint256 timestamp
    );

    // Registra uma identidade (veículo ou empresa)
    function registerIdentity(string memory id) public {
        require(bytes(identities[msg.sender]).length == 0, "Identity already registered");
        identities[msg.sender] = id;
    }

    // Deposita saldo (em wei)
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // Registra uma transação (reserva, recarga ou pagamento)
    function recordTransaction(
        address to,
        uint256 amount,
        string memory transactionType,
        string memory data
    ) public {
        require(balances[msg.sender] >= amount || amount == 0, "Insufficient balance");
        if (amount > 0) {
            balances[msg.sender] -= amount;
            balances[to] += amount;
        }
        transactions.push(Transaction({
            from: msg.sender,
            to: to,
            amount: amount,
            transactionType: transactionType,
            data: data,
            timestamp: block.timestamp
        }));
        emit TransactionRecorded(msg.sender, to, amount, transactionType, data, block.timestamp);
    }

    // Consulta o histórico de transações
    function getTransactions() public view returns (Transaction[] memory) {
        return transactions;
    }

    // Consulta saldo
    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }
}