function somar(){
    const n1 = document.getElementById("n1").value;
    const n2 = document.getElementById("n2").value;
    const soma = Number(n1) + Number(n2);
    document.getElementById("resultado").innerText=soma;
}