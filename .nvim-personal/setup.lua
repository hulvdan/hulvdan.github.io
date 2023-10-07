local opts = { remap = false, silent = true }

require("conform").setup({
    formatters = {
        black = { command = [[.venv\Scripts\black.exe]] },
        isort = { command = [[.venv\Scripts\isort.exe]] },
    },
})

function save_files()
    vim.fn.execute(":wa!")
end

function build()
    vim.g.hulvdan_run_command([[.venv\Scripts\python.exe build.py]])
end

vim.keymap.set("n", "<leader>w", function()
    save_files()

    if vim.bo.filetype == "css" then
        build()
        print("Built!")
    end

    if vim.bo.filetype == "markdown" then
        build()
        print("Built!")
    end

    if vim.bo.filetype == "python" then
        build()
    end
end, opts)
