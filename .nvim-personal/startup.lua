-- vim.fn.execute([[term explorer http://localhost:8000/en.html]])
vim.fn.execute([[term explorer http://localhost:8000]])
vim.fn.execute([[term .venv\Scripts\livereload.exe --host localhost --port 8000 docs]])
-- vim.fn.execute([[e pages/en.md]])
vim.fn.execute([[e pages/index.md]])

vim.defer_fn(function()
    vim.api.nvim_input([[<A-1><C-w>l<A-m>]])
end, 800)
